import logging
from fastapi import APIRouter, HTTPException, status, Query
from app.services.crop.recommendation_service import CropRecommendationService, CropRecommendationInput, CropRecommendationOutput
from app.services.yield_prediction.yield_service import YieldPredictionService, YieldPredictionInput, YieldPredictionOutput
from app.services.crop.fertilizer_service import FertilizerRecommendationService, FertilizerInput, FertilizerRecommendationOutput
from app.services.xai.explanation_model import ExplanationResult
from app.services.xai.xai_service import XAIService
from app.services.xai.shap_explainer import TabularSHAPExplainer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["Machine Learning Intelligence"])

@router.get("/diagnostic")
async def diagnostic():
    import sklearn, joblib
    try:
        import shap
        shap_v = getattr(shap, "__version__", "unknown")
    except ImportError:
        shap_v = "not_installed"
    return {
        "sklearn": getattr(sklearn, "__version__", None),
        "joblib": getattr(joblib, "__version__", None),
        "shap": shap_v,
    }

@router.post("/crop-recommendation", response_model=CropRecommendationOutput)
async def recommend_crop(input_data: CropRecommendationInput):
    """
    ML Crop Recommendation Model (Random Forest, Macro-F1: 0.9955).
    Recommends optimal crops given soil N, P, K, pH, rainfall, and temperature.
    """
    try:
        return CropRecommendationService.predict(input_data)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in recommend_crop: {tb}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{type(e).__name__}: {str(e)} | {tb[-400:]}")

@router.post("/crop-recommendation/explain", response_model=ExplanationResult)
async def explain_crop_recommendation(
    input_data: CropRecommendationInput,
    language: str = Query("en", description="Target locale: en, te, hi, ta, kn, ml")
):
    """
    Returns authentic TreeSHAP feature attributions and structured justification for Crop Recommendation.
    """
    try:
        pred = CropRecommendationService.predict(input_data)
        return XAIService.explain_crop_recommendation(input_data, pred, lang=language)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in explain_crop_recommendation: {tb}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{type(e).__name__}: {str(e)} | {tb[-400:]}")

@router.post("/yield-prediction", response_model=YieldPredictionOutput)
async def predict_yield(input_data: YieldPredictionInput):
    """
    ML Yield Prediction Model (XGBoost Regressor, R2: 0.9574).
    Predicts yield in Quintals/Acre and Tonnes/Ha with confidence interval.
    """
    try:
        return YieldPredictionService.predict(input_data)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in predict_yield: {tb}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{type(e).__name__}: {str(e)} | {tb[-400:]}")

@router.post("/yield-prediction/explain", response_model=ExplanationResult)
async def explain_yield_prediction(
    input_data: YieldPredictionInput,
    language: str = Query("en", description="Target locale: en, te, hi, ta, kn, ml")
):
    """
    Returns authentic TreeSHAP feature attributions and structured justification for Yield Prediction.
    """
    try:
        pred = YieldPredictionService.predict(input_data)
        return XAIService.explain_yield_prediction(input_data, pred, lang=language)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in explain_yield_prediction: {tb}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{type(e).__name__}: {str(e)} | {tb[-400:]}")

@router.post("/fertilizer-recommendation", response_model=FertilizerRecommendationOutput)
async def recommend_fertilizer(input_data: FertilizerInput):
    """
    Agronomic RAG & SafetyEngine Fertilizer and Nutrient Recommendation.
    Validates stage-specific dosage and CIBRC safety restrictions.
    """
    try:
        return FertilizerRecommendationService.recommend(input_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/fertilizer-recommendation/explain", response_model=ExplanationResult)
async def explain_fertilizer_recommendation(
    input_data: FertilizerInput,
    language: str = Query("en", description="Target locale: en, te, hi, ta, kn, ml")
):
    """
    Returns authentic SHAP / agronomic heuristic justification for Fertilizer Recommendation.
    """
    try:
        pred = FertilizerRecommendationService.recommend(input_data)
        model_exp = TabularSHAPExplainer.explain_fertilizer_recommendation(input_data, pred)
        rag_exp = XAIService.create_rag_explanation("SUFFICIENT", lang=language)
        live_exp = XAIService.create_live_data_explanation(lang=language)
        why_bullets = [f.display_text for f in model_exp.top_positive_factors if f.display_text] or [model_exp.explanation_summary]

        return ExplanationResult(
            decision_id="dec_fert_ml",
            decision_type="fertilizer_recommendation",
            prediction=pred.recommended_fertilizer,
            model_name=model_exp.model_name,
            model_version=model_exp.model_version,
            xai_status=model_exp.xai_status,
            model_explanation=model_exp,
            vision_explanation=None,
            rag_evidence=rag_exp,
            live_data=live_exp,
            top_factors=model_exp.top_positive_factors,
            citations=rag_exp.citations,
            confidence=model_exp.confidence,
            why_summary="\n".join([f"- {b}" for b in why_bullets]),
            evidence_summary=rag_exp.explanation_summary,
            current_data_summary=live_exp.summary,
            limitations=[pred.uncertainty_notes] if pred.uncertainty_notes else [],
            locale=language
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.services.crop.recommendation_service import CropRecommendationService, CropRecommendationInput
from app.services.yield_prediction.yield_service import YieldPredictionService, YieldPredictionInput
from app.services.crop.fertilizer_service import FertilizerRecommendationService, FertilizerInput
from app.services.xai.explanation_model import ExplanationResult, ModelExplanation
from app.services.xai.xai_service import XAIService
from app.services.xai.shap_explainer import TabularSHAPExplainer

router = APIRouter(prefix="/xai", tags=["Explainable AI & Model Governance"])


class DecisionExplanationRequest(BaseModel):
    decision_type: str = "crop_recommendation"
    crop_input: Optional[CropRecommendationInput] = None
    yield_input: Optional[YieldPredictionInput] = None
    fertilizer_input: Optional[FertilizerInput] = None
    language: str = "en"


@router.post("/crop-recommendation", response_model=ExplanationResult)
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/yield-prediction", response_model=ExplanationResult)
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/fertilizer-recommendation", response_model=ExplanationResult)
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
            decision_id=f"dec_fert_explain",
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


@router.post("/vision", response_model=ExplanationResult)
async def explain_vision(
    file: UploadFile = File(...),
    crop_hint: Optional[str] = Form("tomato"),
    language: Optional[str] = Form("en")
):
    """
    Returns authentic PyTorch Grad-CAM leaf activation heatmap and localization metadata.
    """
    try:
        image_bytes = await file.read()
        return XAIService.explain_vision_diagnosis(image_bytes=image_bytes, crop_hint=crop_hint, lang=language or "en")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/explain-decision", response_model=ExplanationResult)
async def explain_decision(req: DecisionExplanationRequest):
    """
    Unified decision explainability dispatcher for any supported decision type.
    """
    if req.decision_type == "crop_recommendation" and req.crop_input:
        pred = CropRecommendationService.predict(req.crop_input)
        return XAIService.explain_crop_recommendation(req.crop_input, pred, lang=req.language)
    elif req.decision_type == "yield_prediction" and req.yield_input:
        pred = YieldPredictionService.predict(req.yield_input)
        return XAIService.explain_yield_prediction(req.yield_input, pred, lang=req.language)
    elif req.decision_type == "fertilizer_recommendation" and req.fertilizer_input:
        pred = FertilizerRecommendationService.recommend(req.fertilizer_input)
        model_exp = TabularSHAPExplainer.explain_fertilizer_recommendation(req.fertilizer_input, pred)
        rag_exp = XAIService.create_rag_explanation("SUFFICIENT", lang=req.language)
        live_exp = XAIService.create_live_data_explanation(lang=req.language)
        return ExplanationResult(
            decision_id=f"dec_unified",
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
            why_summary=model_exp.explanation_summary,
            evidence_summary=rag_exp.explanation_summary,
            current_data_summary=live_exp.summary,
            limitations=[pred.uncertainty_notes] if pred.uncertainty_notes else [],
            locale=req.language
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported or incomplete decision inputs.")

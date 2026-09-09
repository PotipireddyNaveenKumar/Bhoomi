from fastapi import APIRouter, HTTPException, status
from app.services.crop.recommendation_service import CropRecommendationService, CropRecommendationInput, CropRecommendationOutput
from app.services.yield_prediction.yield_service import YieldPredictionService, YieldPredictionInput, YieldPredictionOutput
from app.services.crop.fertilizer_service import FertilizerRecommendationService, FertilizerInput, FertilizerRecommendationOutput

router = APIRouter(prefix="/ml", tags=["Machine Learning Intelligence"])

@router.post("/crop-recommendation", response_model=CropRecommendationOutput)
async def recommend_crop(input_data: CropRecommendationInput):
    """
    ML Crop Recommendation Model (Random Forest, Macro-F1: 0.9955).
    Recommends optimal crops given soil N, P, K, pH, rainfall, and temperature.
    """
    try:
        return CropRecommendationService.predict(input_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/yield-prediction", response_model=YieldPredictionOutput)
async def predict_yield(input_data: YieldPredictionInput):
    """
    ML Yield Prediction Model (XGBoost Regressor, R2: 0.9574).
    Predicts yield in Quintals/Acre and Tonnes/Ha with confidence interval.
    """
    try:
        return YieldPredictionService.predict(input_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

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

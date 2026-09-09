from typing import Dict, Any, List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.services.crop.lifecycle_service import CropLifecycleService

router = APIRouter(prefix="/crop", tags=["Crop Intelligence & Recommendation"])

class CropRecommendationRequest(BaseModel):
    N: float = 120.0
    P: float = 40.0
    K: float = 60.0
    temperature: float = 28.0
    humidity: float = 70.0
    ph: float = 6.5
    rainfall_mm: float = 850.0

@router.post("/recommend")
async def recommend_crop(req: CropRecommendationRequest):
    """
    ML Crop Recommendation Abstraction.
    Phase 1 Baseline Provider Interface (Ready for Phase 2 Random Forest/XGBoost benchmarked integration).
    """
    return {
        "status": "success",
        "recommended_crops": [
            {"crop": "Chilli", "confidence": 0.92, "suitability_reason": "Optimal N-P-K balance and warm diurnal temperature profile."},
            {"crop": "Cotton", "confidence": 0.84, "suitability_reason": "High heat tolerance and favorable soil pH match."},
            {"crop": "Maize", "confidence": 0.76, "suitability_reason": "Strong secondary rotation option."}
        ],
        "model_version": "v1.0-baseline"
    }

@router.get("/lifecycle")
async def get_lifecycle(crop: str = Query(default="Chilli"), stage: str = Query(default="vegetative")):
    return CropLifecycleService.get_stage_guidance(crop_name=crop, stage=stage)

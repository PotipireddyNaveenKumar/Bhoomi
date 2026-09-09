from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/yield", tags=["Yield Prediction ML"])

class YieldPredictionRequest(BaseModel):
    crop_name: str = "Chilli"
    area_acres: float = 3.0
    soil_type: str = "black"
    irrigation_type: str = "borewell"
    district: str = "Guntur"
    state: str = "Andhra Pradesh"

@router.post("/predict")
async def predict_yield(req: YieldPredictionRequest):
    """
    ML Yield Prediction Abstraction.
    Phase 1 Baseline Provider Interface (Ready for Phase 2 trained regression models).
    """
    predicted_yield_per_acre = 10.5
    total_yield = round(predicted_yield_per_acre * req.area_acres, 2)
    return {
        "status": "success",
        "crop_name": req.crop_name,
        "area_acres": req.area_acres,
        "predicted_yield_quintals_per_acre": predicted_yield_per_acre,
        "total_estimated_production_quintals": total_yield,
        "confidence_interval_quintals": [round(total_yield * 0.9, 1), round(total_yield * 1.1, 1)],
        "model_version": "v1.0-baseline-regressor"
    }

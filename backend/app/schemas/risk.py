from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RiskDimension(BaseModel):
    category: str  # Weather Risk, Yield Risk, Market Risk, Crop Health Risk, Economic Risk
    score: int     # 1 to 100
    level: str     # LOW, MODERATE, HIGH, SEVERE
    factors: List[str]
    mitigation_actions: List[str]

class RiskAssessmentRequest(BaseModel):
    crop_name: str = Field(..., example="Chilli")
    crop_stage: str = Field(..., example="flowering")
    location: str = Field(..., example="Guntur")
    area_acres: float = Field(..., example=3.0)
    irrigation_available: bool = True
    rainfall_forecast_status: Optional[str] = "moderate"

class RiskAssessmentResponse(BaseModel):
    overall_risk_score: int
    overall_risk_level: str
    summary: str
    dimensions: List[RiskDimension]

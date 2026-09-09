from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class VisionTopPrediction(BaseModel):
    class_id: int
    class_name: str
    disease_key: str
    common_name: str
    confidence: float
    calibrated_confidence: float

class VisionPrediction(BaseModel):
    crop: str = "tomato"
    disease: str
    common_name: str
    confidence: float
    calibrated_confidence: float
    model_version: str = "tomato_vision_v1.0"
    top_predictions: List[VisionTopPrediction] = []
    quality_status: str = "PASSED"  # PASSED, FAILED
    uncertainty_status: str = "LOW"  # LOW, MODERATE, HIGH, UNRELIABLE
    is_ood: bool = False
    inference_time_ms: float = 0.0
    quality_metrics: Dict[str, Any] = {}
    is_reliable: bool = True

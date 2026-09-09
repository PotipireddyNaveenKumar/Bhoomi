from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class PredictionLog(BaseModel):
    model_name: str
    model_version: str
    input_features_hash: str
    predicted_class_or_value: Any
    confidence_score: float
    latency_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ModelHealthMetrics(BaseModel):
    model_name: str
    total_inferences: int
    mean_confidence: float
    average_latency_ms: float
    feedback_ratings: Dict[str, int]
    drift_alert: bool
    status: str  # HEALTHY, MONITORING, DRIFT_DETECTED

class ModelMonitoringService:
    """
    Model Monitoring and Observability Service.
    Tracks prediction health, confidence distributions, inference latencies,
    and user feedback without logging sensitive tokens or PII.
    """
    _logs: Dict[str, List[PredictionLog]] = {
        "crop_recommendation": [],
        "yield_prediction": [],
        "vision_pathology": []
    }
    _feedback_counts: Dict[str, Dict[str, int]] = {
        "crop_recommendation": {"USEFUL": 0, "PARTIAL": 0, "NOT_USEFUL": 0},
        "yield_prediction": {"USEFUL": 0, "PARTIAL": 0, "NOT_USEFUL": 0},
        "vision_pathology": {"USEFUL": 0, "PARTIAL": 0, "NOT_USEFUL": 0}
    }

    @classmethod
    def log_inference(
        cls,
        model_name: str,
        predicted_val: Any,
        confidence: float,
        latency_ms: float,
        version: str = "2.0-production"
    ):
        if model_name not in cls._logs:
            cls._logs[model_name] = []
        cls._logs[model_name].append(PredictionLog(
            model_name=model_name,
            model_version=version,
            input_features_hash=f"hash_{len(cls._logs[model_name]) + 100}",
            predicted_class_or_value=predicted_val,
            confidence_score=confidence,
            latency_ms=latency_ms
        ))

    @classmethod
    def record_model_feedback(cls, model_name: str, rating: str):
        if model_name in cls._feedback_counts and rating in cls._feedback_counts[model_name]:
            cls._feedback_counts[model_name][rating] += 1

    @classmethod
    def get_metrics(cls, model_name: str) -> ModelHealthMetrics:
        logs = cls._logs.get(model_name, [])
        total = len(logs)
        if total == 0:
            return ModelHealthMetrics(
                model_name=model_name,
                total_inferences=0,
                mean_confidence=1.0,
                average_latency_ms=15.0,
                feedback_ratings=cls._feedback_counts.get(model_name, {}),
                drift_alert=False,
                status="HEALTHY"
            )

        mean_conf = sum(l.confidence_score for l in logs) / total
        avg_latency = sum(l.latency_ms for l in logs) / total
        drift = mean_conf < 0.70  # Flag drift if average confidence drops below 70%

        return ModelHealthMetrics(
            model_name=model_name,
            total_inferences=total,
            mean_confidence=round(mean_conf, 3),
            average_latency_ms=round(avg_latency, 2),
            feedback_ratings=cls._feedback_counts.get(model_name, {}),
            drift_alert=drift,
            status="DRIFT_DETECTED" if drift else "HEALTHY"
        )

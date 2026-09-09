import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class FeedbackStatus:
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
    FOLLOWED = "FOLLOWED"
    NOT_FOLLOWED = "NOT_FOLLOWED"
    SUCCESSFUL = "SUCCESSFUL"
    UNSUCCESSFUL = "UNSUCCESSFUL"
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    # Legacy aliases
    USEFUL = "USEFUL"
    PARTIAL = "PARTIAL"
    NOT_USEFUL = "NOT_USEFUL"


class RecommendationRecord(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:10]}")
    farmer_id: str
    farm_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    intent: str
    decision_type: str = ""
    input_context: Dict[str, Any] = Field(default_factory=dict)
    data_freshness: Dict[str, str] = Field(default_factory=dict)
    tools_used: List[str] = Field(default_factory=list)
    model_versions: Dict[str, str] = Field(default_factory=dict)
    rag_sources: List[str] = Field(default_factory=list)
    weather_source: Optional[str] = None
    market_source: Optional[str] = None
    calculations: Dict[str, Any] = Field(default_factory=dict)
    safety_checks: List[str] = Field(default_factory=list)
    recommendation_text: str
    confidence: float
    assumptions: List[str] = Field(default_factory=list)
    farmer_action: str = "PENDING"  # ACCEPTED, MODIFIED, REJECTED, FOLLOWED, NOT_FOLLOWED, PENDING
    outcome: Optional[str] = None
    feedback_rating: Optional[str] = None  # HELPFUL, NOT_HELPFUL, SUCCESSFUL, UNSUCCESSFUL, CORRECT, INCORRECT
    feedback_notes: Optional[str] = None


class RecommendationTraceStore:
    """
    Audit and explainability repository for all high-impact AI farm decisions.
    Records full provenance and captures structured farmer feedback without automated retraining.
    """
    _traces: Dict[str, RecommendationRecord] = {}

    @classmethod
    def record_trace(cls, record: RecommendationRecord) -> RecommendationRecord:
        cls._traces[record.recommendation_id] = record
        return record

    @classmethod
    def get_trace(cls, recommendation_id: str) -> Optional[RecommendationRecord]:
        return cls._traces.get(recommendation_id)

    @classmethod
    def update_feedback(
        cls,
        recommendation_id: str,
        farmer_action: str,
        feedback_rating: Optional[str] = None,
        feedback_notes: Optional[str] = None
    ) -> Optional[RecommendationRecord]:
        rec = cls._traces.get(recommendation_id)
        if rec:
            rec.farmer_action = farmer_action
            rec.feedback_rating = feedback_rating
            rec.feedback_notes = feedback_notes
        return rec

    @classmethod
    def list_for_farmer(cls, farmer_id: str) -> List[RecommendationRecord]:
        return [r for r in cls._traces.values() if r.farmer_id == farmer_id]

    @classmethod
    def get_traces_for_farmer(cls, farmer_id: str) -> List[RecommendationRecord]:
        return cls.list_for_farmer(farmer_id)


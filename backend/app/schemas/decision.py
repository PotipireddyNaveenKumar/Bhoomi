from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    IRRIGATION = "IRRIGATION"
    SPRAYING = "SPRAYING"
    FERTILIZATION = "FERTILIZATION"
    CROP_HEALTH = "CROP_HEALTH"
    HARVEST = "HARVEST"
    MARKET_SELL = "MARKET_SELL"
    MARKET_WAIT = "MARKET_WAIT"
    CROP_PLANNING = "CROP_PLANNING"
    WEATHER_RESPONSE = "WEATHER_RESPONSE"
    RISK = "RISK"
    TASK = "TASK"
    GENERAL_FARM_ACTION = "GENERAL_FARM_ACTION"


class DecisionPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class DecisionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    EXECUTED = "EXECUTED"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class FarmDecision(BaseModel):
    decision_id: str
    farmer_id: str
    farm_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decision_type: DecisionType
    priority: DecisionPriority
    status: DecisionStatus = DecisionStatus.PROPOSED

    title: str
    summary: str
    recommended_action: str

    reason: str
    evidence: str

    confidence: ConfidenceLevel
    confidence_score: float = 0.85
    uncertainty: str = "LOW"

    deadline: str = "Today"
    valid_until: str = "Within 48 hours"

    data_freshness: Dict[str, str] = Field(default_factory=dict)

    risks: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)

    alternative_actions: List[str] = Field(default_factory=list)
    required_information: List[str] = Field(default_factory=list)

    source_tools: List[str] = Field(default_factory=list)
    model_versions: Dict[str, str] = Field(default_factory=dict)

    safety_status: str = "VERIFIED_SAFE"
    trace_id: str = ""

    # Backwards-compatible aliases for legacy DecisionItem consumers
    @property
    def action(self) -> str:
        return self.recommended_action

    @property
    def category(self) -> str:
        return self.decision_type.value

    @property
    def urgency(self) -> str:
        return "IMMEDIATE" if self.priority == DecisionPriority.CRITICAL else "WITHIN_24_HOURS" if self.priority == DecisionPriority.HIGH else "WITHIN_3_DAYS"

    @property
    def expected_benefit(self) -> str:
        return self.summary

    @property
    def risk_if_ignored(self) -> str:
        return self.risks[0] if self.risks else "Sub-optimal crop yield or avoidable cost."

    @property
    def required_farmer_confirmation(self) -> bool:
        return self.priority in [DecisionPriority.CRITICAL, DecisionPriority.HIGH]


class DecisionPlan(BaseModel):
    farmer_id: str
    farm_summary: str
    current_crop: str
    crop_stage: str
    top_decisions: List[FarmDecision]
    weather_action: FarmDecision
    irrigation_action: FarmDecision
    health_action: FarmDecision
    market_action: Optional[FarmDecision] = None
    overall_confidence: float = 0.90
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: str = ""


class DecisionEvaluationRequest(BaseModel):
    farmer_id: Optional[str] = None
    farm_id: Optional[str] = None
    intent: Optional[str] = None
    user_question: Optional[str] = None


class DecisionEvaluationResponse(BaseModel):
    success: bool = True
    plan: DecisionPlan
    missing_information: List[str] = Field(default_factory=list)
    conflicts_resolved: List[Dict[str, Any]] = Field(default_factory=list)
    active_risks: List[Dict[str, Any]] = Field(default_factory=list)


class DecisionTraceResponse(BaseModel):
    id: str
    decision_id: str
    recommendation_id: str
    farmer_id: str
    farm_id: Optional[str] = None
    decision_type: Optional[str] = None
    intent: Optional[str] = None
    created_at: str
    updated_at: str
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
    confidence: float = 1.0
    assumptions: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    xai_info: Dict[str, Any] = Field(default_factory=dict)
    farmer_action: str = "PENDING"
    outcome: Optional[str] = None
    feedback_rating: Optional[str] = None
    feedback_notes: Optional[str] = None
    locale: str = "en"
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class DecisionHistoryResponse(BaseModel):
    success: bool = True
    total: int
    limit: int
    offset: int
    decisions: List[DecisionTraceResponse]

from typing import Optional, Dict, Any, List
from datetime import date, datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.decision import DecisionPriority, ConfidenceLevel


class TaskType(str, Enum):
    IRRIGATION = "IRRIGATION"
    FIELD_INSPECTION = "FIELD_INSPECTION"
    CROP_HEALTH_SCOUTING = "CROP_HEALTH_SCOUTING"
    FERTILIZATION = "FERTILIZATION"
    SPRAYING = "SPRAYING"
    WEED_MANAGEMENT = "WEED_MANAGEMENT"
    PEST_MONITORING = "PEST_MONITORING"
    DISEASE_MONITORING = "DISEASE_MONITORING"
    HARVEST_PREPARATION = "HARVEST_PREPARATION"
    HARVEST = "HARVEST"
    MARKET_CHECK = "MARKET_CHECK"
    SOIL_CHECK = "SOIL_CHECK"
    GENERAL_FARM_TASK = "GENERAL_FARM_TASK"


class TaskPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class TaskStatus(str, Enum):
    PLANNED = "PLANNED"
    DUE = "DUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    POSTPONED = "POSTPONED"
    SKIPPED = "SKIPPED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class CropLifecycleState(BaseModel):
    crop: str
    variety: Optional[str] = None
    sowing_date: Optional[str] = None
    transplant_date: Optional[str] = None
    current_stage: str
    stage_started_at: Optional[str] = None
    expected_next_stage: Optional[str] = None
    expected_harvest_date: Optional[str] = None
    harvest_window_start: Optional[str] = None
    harvest_window_end: Optional[str] = None
    stage_confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    data_source: str = "calculated"  # farmer_recorded, calculated, estimated, unknown
    reason: Optional[str] = None
    days_after_sowing: Optional[int] = None
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FarmTask(BaseModel):
    task_id: str
    farm_id: str
    crop: str
    task_type: TaskType
    title: str
    description: Optional[str] = None
    priority: DecisionPriority = DecisionPriority.MEDIUM
    status: TaskStatus = TaskStatus.PLANNED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    due_at: str
    expires_at: Optional[str] = None
    crop_stage: Optional[str] = None
    stage_dependency: Optional[str] = None
    weather_dependency: Optional[Dict[str, Any]] = None
    soil_dependency: Optional[Dict[str, Any]] = None
    health_dependency: Optional[Dict[str, Any]] = None
    trigger: str
    reason: str
    evidence: Optional[str] = None
    source_references: List[str] = Field(default_factory=list)
    safety_status: str = "VERIFIED_SAFE"
    completion_status: Optional[str] = None
    completed_at: Optional[str] = None
    completion_source: Optional[str] = None
    postponed_at: Optional[str] = None
    postponement_reason: Optional[str] = None
    old_due_time: Optional[str] = None
    new_due_time: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    trace_id: str = ""
    weather_freshness: str = "CURRENT"

    @property
    def is_overdue(self) -> bool:
        if self.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.CANCELLED, TaskStatus.POSTPONED]:
            return False
        try:
            # Handle date or datetime strings
            due_dt = datetime.fromisoformat(self.due_at.replace("Z", "+00:00"))
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > due_dt
        except Exception:
            return False


# --- Backwards compatibility models for existing DB/API routes ---
class FarmTaskCreate(BaseModel):
    farm_id: str
    crop_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    task_type: str = "pest_monitoring"
    priority: str = "medium"
    due_date: date
    reason: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None


class FarmTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    reason: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None


class FarmTaskResponse(FarmTaskCreate):
    id: str
    farmer_id: str
    status: str
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


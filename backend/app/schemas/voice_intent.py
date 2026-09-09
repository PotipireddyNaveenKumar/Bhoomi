import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.schemas.task import TaskType


class VoiceIntentType(str, Enum):
    GENERAL_GREETING = "GENERAL_GREETING"
    GENERAL_AGRICULTURE = "GENERAL_AGRICULTURE"
    GENERAL_AGRICULTURE_QUERY = "GENERAL_AGRICULTURE"  # Alias
    CROP_RECOMMENDATION = "CROP_RECOMMENDATION"
    CROP_SELECTION = "CROP_SELECTION"
    CROP_STATUS = "CROP_STATUS"
    CROP_STAGE = "CROP_STAGE"
    CROP_MANAGEMENT = "CROP_MANAGEMENT"
    WEATHER_QUERY = "WEATHER_QUERY"
    SPRAY_WEATHER_SAFETY = "SPRAY_WEATHER_SAFETY"
    IRRIGATION_QUERY = "IRRIGATION_QUERY"
    FERTILIZER_QUERY = "FERTILIZER_QUERY"
    PEST_QUERY = "PEST_QUERY"
    DISEASE_QUERY = "DISEASE_QUERY"
    CROP_HEALTH_QUERY = "CROP_HEALTH_QUERY"
    VISION_DIAGNOSIS = "VISION_DIAGNOSIS"
    MARKET_QUERY = "MARKET_QUERY"
    SELL_DECISION = "SELL_DECISION"
    HARVEST_QUERY = "HARVEST_QUERY"
    PROFIT_QUERY = "PROFIT_QUERY"
    SIMULATION_QUERY = "SIMULATION_QUERY"
    TASK_TODAY = "TASK_TODAY"
    TASK_WEEK = "TASK_WEEK"
    TASK_PENDING = "TASK_PENDING"
    TASK_DETAILS = "TASK_DETAILS"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_POSTPONE = "TASK_POSTPONE"
    TASK_SKIP = "TASK_SKIP"
    TASK_STATUS = "TASK_STATUS"
    TASK_WHY = "TASK_WHY"
    FARM_STATUS = "FARM_STATUS"
    FARM_CHANGES = "FARM_CHANGES"
    FARM_PROFILE = "FARM_PROFILE"
    HELP = "HELP"
    LANGUAGE_CHANGE = "LANGUAGE_CHANGE"
    CONFIRM = "CONFIRM"
    TASK_CONFIRM = "CONFIRM"  # Alias
    CANCEL = "CANCEL"
    TASK_CANCEL_ACTION = "CANCEL"  # Alias
    SAFETY_QUERY = "SAFETY_QUERY"
    AGRICULTURAL_NEWS = "AGRICULTURAL_NEWS"
    UNKNOWN = "UNKNOWN"


class VoiceIntent(BaseModel):
    intent_id: str = Field(default_factory=lambda: f"intent_{uuid.uuid4().hex[:10]}")
    intent_type: VoiceIntentType
    language: str = "en"
    raw_transcript: str = ""
    normalized_text: str = ""
    confidence: float = 1.0
    entities: Dict[str, Any] = Field(default_factory=dict)
    target_task_id: Optional[str] = None
    target_crop: Optional[str] = None
    target_task_type: Optional[TaskType] = None
    requested_date: Optional[str] = None
    requested_delay_days: Optional[int] = None
    requested_time: Optional[str] = None
    confirmation_required: bool = False
    trace_id: str = ""


class FeedbackOutcome(str, Enum):
    SUCCESSFUL = "SUCCESSFUL"
    PARTIALLY_SUCCESSFUL = "PARTIALLY_SUCCESSFUL"
    NOT_SUCCESSFUL = "NOT_SUCCESSFUL"
    UNKNOWN = "UNKNOWN"


class TaskFeedback(BaseModel):
    feedback_id: str = Field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:10]}")
    task_id: str
    farmer_id: str
    rating: Optional[int] = None  # 1-5 scale
    outcome: FeedbackOutcome = FeedbackOutcome.UNKNOWN
    comment: Optional[str] = None
    language: str = "en"
    source: str = "farmer_voice"  # farmer_voice, farmer_text, api
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: str = ""

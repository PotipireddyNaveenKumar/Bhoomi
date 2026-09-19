import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.schemas.task import TaskType


class VoiceIntentType(str, Enum):
    # Core Conversational & Knowledge
    GENERAL_GREETING = "GENERAL_GREETING"
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    GENERAL_AGRICULTURE = "GENERAL_AGRICULTURE"
    GENERAL_AGRICULTURE_QUERY = "GENERAL_AGRICULTURE"
    AGRICULTURAL_KNOWLEDGE = "AGRICULTURAL_KNOWLEDGE"

    # Crop Planning & Lifecycle
    CROP_RECOMMENDATION = "CROP_RECOMMENDATION"
    CROP_COMPARISON = "CROP_COMPARISON"
    CROP_SELECTION = "CROP_SELECTION"
    CROP_STATUS = "CROP_STATUS"
    CROP_STAGE = "CROP_STAGE"
    CROP_MANAGEMENT = "CROP_MANAGEMENT"

    # Canonical Weather & Meteorological Decisions
    CURRENT_WEATHER = "CURRENT_WEATHER"
    TODAY_WEATHER = "TODAY_WEATHER"
    TOMORROW_FORECAST = "TOMORROW_FORECAST"
    MULTI_DAY_FORECAST = "MULTI_DAY_FORECAST"
    RAIN_FORECAST = "RAIN_FORECAST"
    SPRAY_WINDOW_FORECAST = "SPRAY_WINDOW_FORECAST"
    IRRIGATION_FORECAST = "IRRIGATION_FORECAST"

    # Weather Legacy Aliases
    WEATHER_QUERY = "WEATHER_QUERY"
    WEATHER_CURRENT = "WEATHER_CURRENT"
    WEATHER_FORECAST = "WEATHER_FORECAST"
    WEATHER_RAIN = "WEATHER_RAIN"
    SPRAY_WEATHER_SAFETY = "SPRAY_WEATHER_SAFETY"
    IRRIGATION_DECISION = "IRRIGATION_DECISION"
    IRRIGATION_QUERY = "IRRIGATION_QUERY"

    # Agronomy & Crop Protection
    FERTILIZER_ADVICE = "FERTILIZER_ADVICE"
    FERTILIZER_QUERY = "FERTILIZER_QUERY"
    PEST_QUERY = "PEST_QUERY"
    DISEASE_QUERY = "DISEASE_QUERY"
    DISEASE_DIAGNOSIS = "DISEASE_DIAGNOSIS"
    CROP_HEALTH = "CROP_HEALTH"
    CROP_HEALTH_QUERY = "CROP_HEALTH_QUERY"
    VISION_DIAGNOSIS = "VISION_DIAGNOSIS"

    # Canonical Market, Mandi & Selling
    MARKET_PRICE = "MARKET_PRICE"
    MARKET_TREND = "MARKET_TREND"
    MARKET_COMPARISON = "MARKET_COMPARISON"
    MARKET_ARRIVALS = "MARKET_ARRIVALS"
    MARKET_LOCATION_SEARCH = "MARKET_LOCATION_SEARCH"

    # Market Legacy Aliases
    MARKET_QUERY = "MARKET_QUERY"
    MARKET_CURRENT = "MARKET_CURRENT"
    MARKET_COMPARE = "MARKET_COMPARE"
    MARKET_SELL_DECISION = "MARKET_SELL_DECISION"
    SELL_DECISION = "SELL_DECISION"
    HARVEST_QUERY = "HARVEST_QUERY"
    HARVEST_DECISION = "HARVEST_DECISION"

    # Finance, Profit & Simulation
    PROFIT_QUERY = "PROFIT_QUERY"
    PROFIT_ANALYSIS = "PROFIT_ANALYSIS"
    FINANCE_CALCULATION = "FINANCE_CALCULATION"
    SIMULATION_QUERY = "SIMULATION_QUERY"
    WHAT_IF_SIMULATION = "WHAT_IF_SIMULATION"

    # Farm Tasks & Briefing
    TODAY_PLAN = "TODAY_PLAN"
    WEEKLY_PLAN = "WEEKLY_PLAN"
    TASK_QUERY = "TASK_QUERY"
    TASK_ACTION = "TASK_ACTION"
    TASK_TODAY = "TASK_TODAY"
    TASK_WEEK = "TASK_WEEK"
    TASK_PENDING = "TASK_PENDING"
    TASK_DETAILS = "TASK_DETAILS"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_POSTPONE = "TASK_POSTPONE"
    TASK_SKIP = "TASK_SKIP"
    TASK_STATUS = "TASK_STATUS"
    TASK_WHY = "TASK_WHY"

    # Digital Twin, Memory & News
    FARM_STATUS = "FARM_STATUS"
    FARM_CHANGES = "FARM_CHANGES"
    FARM_PROFILE = "FARM_PROFILE"
    MEMORY_QUERY = "MEMORY_QUERY"
    GOVERNMENT_SCHEME = "GOVERNMENT_SCHEME"
    AGRICULTURAL_NEWS = "AGRICULTURAL_NEWS"

    # Feedback & Escalation
    FEEDBACK = "FEEDBACK"
    EXPERT_ESCALATION = "EXPERT_ESCALATION"

    # State Machine & Fallbacks
    HELP = "HELP"
    LANGUAGE_CHANGE = "LANGUAGE_CHANGE"
    CONFIRM = "CONFIRM"
    TASK_CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
    TASK_CANCEL_ACTION = "CANCEL"
    SAFETY_QUERY = "SAFETY_QUERY"
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

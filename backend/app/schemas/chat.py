from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

class ChatMessageCreate(BaseModel):
    session_id: Optional[str] = None
    content: str = Field(..., example="What should I do this week?")
    input_mode: str = Field(default="text", example="text")  # text, voice, image
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    language: Optional[str] = Field(default=None, example="en")
    language_code: Optional[str] = Field(default=None, example="en")

    @model_validator(mode="before")
    @classmethod
    def sync_language_fields(cls, values):
        if isinstance(values, dict):
            lang_code = values.get("language_code")
            lang = values.get("language")
            if lang_code and not lang:
                values["language"] = lang_code
            elif lang and not lang_code:
                values["language_code"] = lang
            elif not lang and not lang_code:
                values["language"] = "en"
                values["language_code"] = "en"
        return values

class VisualCard(BaseModel):
    card_type: str  # weather_card, market_card, crop_plan_card, profit_card, risk_card, simulation_card, task_card
    title: str
    subtitle: Optional[str] = None
    data: Dict[str, Any]

class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    sender: str  # user, assistant
    input_mode: str
    content: str
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    visual_cards: List[VisualCard] = []
    structured_payload: Optional[Dict[str, Any]] = None
    voice_state: str = "RESPONDING"
    intent: Optional[str] = None
    trace_id: Optional[str] = None
    sources: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    id: str
    farmer_id: str
    title: str
    language: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True

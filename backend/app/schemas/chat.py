from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ChatMessageCreate(BaseModel):
    session_id: Optional[str] = None
    content: str = Field(..., example="What should I do this week?")
    input_mode: str = Field(default="text", example="text")  # text, voice, image
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    language: Optional[str] = Field(default="en", example="en")

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

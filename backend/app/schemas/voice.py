from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class TranscriptionResponse(BaseModel):
    text: str
    language_code: str
    confidence: float = 1.0
    provider: str

class SynthesisRequest(BaseModel):
    text: str
    language_code: str = "en"
    speaker_gender: str = "female"

class SynthesisResponse(BaseModel):
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    provider: str
    duration_seconds: Optional[float] = None

class VoiceInteractResponse(BaseModel):
    user_transcription: str
    detected_language: str
    assistant_text: str
    assistant_audio_url: Optional[str] = None
    assistant_audio_base64: Optional[str] = None
    visual_cards: List[Dict[str, Any]] = []
    session_id: str
    message_id: str
    voice_state: str = "RESPONDING"


class VoiceTaskActionRequest(BaseModel):
    audio: Optional[str] = None  # base64 encoded audio
    text: Optional[str] = None
    language: Optional[str] = "en"
    farmer_id: Optional[str] = "farmer_demo_1"
    conversation_id: Optional[str] = "session_demo_1"


class VoiceTaskActionResponse(BaseModel):
    intent: str
    task_id: Optional[str] = None
    action: str
    status: str
    requires_confirmation: bool = False
    response_text: str
    language: str = "en"
    trace_id: str = ""


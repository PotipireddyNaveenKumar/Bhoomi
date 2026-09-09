from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class TranscriptionResult(BaseModel):
    text: str
    language_code: str
    confidence: float = 1.0
    provider: str

class SynthesisResult(BaseModel):
    audio_bytes: bytes
    content_type: str = "audio/wav"
    provider: str
    duration_seconds: Optional[float] = None

class VoiceProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language_code: Optional[str] = None) -> TranscriptionResult:
        """Transcribe speech audio into text with language detection."""
        pass

    @abstractmethod
    async def synthesize(self, text: str, language_code: str = "en", speaker_gender: str = "female") -> SynthesisResult:
        """Synthesize text into speech audio."""
        pass

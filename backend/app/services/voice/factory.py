import os
import logging
from typing import Optional
from app.core.config import settings
from app.services.voice.base import VoiceProvider
from app.services.voice.sarvam import SarvamVoiceProvider
from app.services.voice.mock import MockVoiceProvider

logger = logging.getLogger(__name__)

def get_voice_provider(provider_name: Optional[str] = None) -> VoiceProvider:
    """
    Factory resolving active VoiceProvider based on VOICE_PROVIDER environment variable.
    Preserves MockVoiceProvider as safe fallback for offline tests and CI/CD.
    """
    name = (provider_name or os.environ.get("VOICE_PROVIDER") or settings.VOICE_PROVIDER).lower().strip()
    
    if name == "sarvam":
        if "SARVAM_API_KEY" in os.environ:
            api_key = os.environ["SARVAM_API_KEY"]
        else:
            api_key = settings.SARVAM_API_KEY
        if api_key and not api_key.startswith("your_"):
            return SarvamVoiceProvider(api_key=api_key)
        if settings.is_production:
            raise RuntimeError(
                "Production configuration error: SARVAM_API_KEY must be provided when VOICE_PROVIDER='sarvam'. "
                "Silent fallback to MockVoiceProvider is disabled in production."
            )
        logger.warning("SARVAM_API_KEY not configured or placeholder detected. Falling back safely to MockVoiceProvider.")
        return MockVoiceProvider()
    elif name == "bhashini":
        if settings.is_production:
            raise RuntimeError(
                "Production configuration error: Voice provider 'bhashini' is not supported in production."
            )
        return MockVoiceProvider()
    elif name == "whisper":
        if settings.is_production:
            raise RuntimeError(
                "Production configuration error: Voice provider 'whisper' is not supported in production."
            )
        return MockVoiceProvider()
    else:
        return MockVoiceProvider()

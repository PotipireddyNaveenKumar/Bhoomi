import base64
import logging
from typing import Optional, Dict, Any
import httpx
from fastapi import status
from app.core.config import settings
from app.core.exceptions import VoiceProcessingException
from app.services.voice.base import VoiceProvider, TranscriptionResult, SynthesisResult

logger = logging.getLogger(__name__)

_KEY_SENTINEL = object()

class SarvamVoiceProvider(VoiceProvider):
    """
    Production Sarvam AI STT (saaras:v3) & TTS (bulbul:v3) Provider implementation.
    Maintains six-language support (en, te, hi, ta, kn, ml) with automatic normalization.
    API keys remain safely configured on the backend only; never leaked in logs or errors.
    """
    # Supported BCP-47 language mappings for Sarvam
    SUPPORTED_LANGUAGES = {
        "te": "te-IN",
        "hi": "hi-IN",
        "ta": "ta-IN",
        "kn": "kn-IN",
        "ml": "ml-IN",
        "en": "en-IN"
    }

    # Best available neural voice speakers per language in bulbul:v3
    LANGUAGE_SPEAKERS = {
        "te": {"female": "kavitha", "male": "mani"},
        "hi": {"female": "kavya", "male": "rahul"},
        "ta": {"female": "kavitha", "male": "mani"},
        "kn": {"female": "roopa", "male": "mani"},
        "ml": {"female": "kavitha", "male": "mani"},
        "en": {"female": "kavya", "male": "aditya"},
    }

    MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit

    def __init__(
        self,
        api_key: Any = _KEY_SENTINEL,
        stt_model: Optional[str] = None,
        tts_model: Optional[str] = None,
        timeout: float = 25.0
    ):
        if api_key is _KEY_SENTINEL:
            self._api_key = settings.SARVAM_API_KEY
        else:
            self._api_key = api_key
        self.stt_model = stt_model or settings.SARVAM_STT_MODEL
        self.tts_model = tts_model or settings.SARVAM_TTS_MODEL
        self.timeout = timeout
        self.stt_url = "https://api.sarvam.ai/speech-to-text"
        self.tts_url = "https://api.sarvam.ai/text-to-speech"

    def normalize_language_code(self, lang: Optional[str]) -> str:
        """Normalizes input language string into BHOOMI 2-letter code."""
        if not lang or lang.lower() == "auto":
            return "en"
        code = lang.lower().split("-")[0].strip()
        if code in self.SUPPORTED_LANGUAGES:
            return code
        return "en"

    def get_sarvam_language_tag(self, lang: Optional[str]) -> str:
        """Returns the BCP-47 tag required by Sarvam API (e.g. te-IN)."""
        base = self.normalize_language_code(lang)
        return self.SUPPORTED_LANGUAGES.get(base, "en-IN")

    def get_speaker(self, lang: str, gender: str = "female") -> str:
        """Resolves the best available speaker in bulbul:v3 for given language and gender."""
        base_lang = self.normalize_language_code(lang)
        speakers = self.LANGUAGE_SPEAKERS.get(base_lang, self.LANGUAGE_SPEAKERS["en"])
        return speakers.get(gender.lower(), speakers.get("female", "kavya"))

    async def transcribe(self, audio_bytes: bytes, language_code: Optional[str] = None) -> TranscriptionResult:
        """
        Transcribes speech audio bytes to text via Sarvam saaras STT.
        Validates audio payload and gracefully handles network/provider errors.
        """
        if not self._api_key or self._api_key.startswith("your_"):
            raise VoiceProcessingException("SARVAM_API_KEY is not configured on the server.")

        if not audio_bytes or len(audio_bytes) == 0:
            raise VoiceProcessingException("Audio payload is empty.")

        if len(audio_bytes) > self.MAX_AUDIO_SIZE_BYTES:
            raise VoiceProcessingException(f"Audio file exceeds maximum size of {self.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB.")

        headers = {
            "api-subscription-key": self._api_key,
        }

        target_lang = self.get_sarvam_language_tag(language_code) if language_code and language_code != "auto" else None

        # Auto-detect audio container format from header magic bytes
        if audio_bytes.startswith(b"\x1aE\xdf\xa3"):
            audio_filename, audio_mime = "audio.webm", "audio/webm"
        elif audio_bytes.startswith(b"OggS"):
            audio_filename, audio_mime = "audio.ogg", "audio/ogg"
        elif audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xff\xfb") or audio_bytes.startswith(b"\xff\xf3"):
            audio_filename, audio_mime = "audio.mp3", "audio/mpeg"
        elif audio_bytes.startswith(b"RIFF") and audio_bytes[8:12] == b"WAVE":
            audio_filename, audio_mime = "audio.wav", "audio/wav"
        else:
            audio_filename, audio_mime = "audio.wav", "audio/wav"

        files = {
            "file": (audio_filename, audio_bytes, audio_mime)
        }
        data: Dict[str, str] = {
            "model": self.stt_model,
        }
        if target_lang:
            data["language_code"] = target_lang

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.stt_url, headers=headers, data=data, files=files)

                if response.status_code == 401 or response.status_code == 403:
                    logger.error("Sarvam STT authentication failed (401/403).")
                    raise VoiceProcessingException("Sarvam STT provider authentication error. Please verify server credentials.", status_code=status.HTTP_502_BAD_GATEWAY)

                if response.status_code == 402:
                    logger.warning("Sarvam STT quota/credits exhausted (402).")
                    raise VoiceProcessingException("Sarvam AI speech recognition credits exhausted (HTTP 402). Please check account credits.", status_code=status.HTTP_402_PAYMENT_REQUIRED)

                if response.status_code == 429:
                    logger.warning("Sarvam STT rate limit exceeded (429).")
                    raise VoiceProcessingException("Voice service is currently busy (Rate Limit). Please try again shortly.", status_code=status.HTTP_429_TOO_MANY_REQUESTS)

                if response.status_code != 200:
                    err_msg = "Voice service encountered an error processing your audio."
                    try:
                        err_body = response.json()
                        if isinstance(err_body, dict) and "error" in err_body:
                            api_msg = err_body["error"].get("message") if isinstance(err_body["error"], dict) else str(err_body["error"])
                            if api_msg:
                                err_msg = f"Voice recognition error: {api_msg}"
                    except Exception:
                        pass
                    logger.error(f"Sarvam STT returned HTTP {response.status_code}: {err_msg}")
                    raise VoiceProcessingException(err_msg, status_code=response.status_code if 400 <= response.status_code < 600 else status.HTTP_502_BAD_GATEWAY)

                result = response.json()
                transcript = result.get("transcript", "").strip()
                detected_sarvam_lang = result.get("language_code")
                norm_lang = self.normalize_language_code(detected_sarvam_lang or language_code)
                confidence = float(result.get("confidence", 1.0) or 1.0)

                return TranscriptionResult(
                    text=transcript,
                    language_code=norm_lang,
                    confidence=confidence,
                    provider="sarvam"
                )

        except httpx.TimeoutException:
            logger.warning("Sarvam STT call timed out.")
            raise VoiceProcessingException("Voice recognition request timed out. Please try speaking again.", status_code=status.HTTP_504_GATEWAY_TIMEOUT)
        except httpx.RequestError as exc:
            logger.error(f"Network error calling Sarvam STT: {type(exc).__name__}")
            raise VoiceProcessingException("Unable to connect to speech recognition service. Check your internet connection.", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        except VoiceProcessingException:
            raise
        except Exception as exc:
            logger.error(f"Unexpected error in Sarvam STT: {type(exc).__name__}")
            raise VoiceProcessingException("Unexpected error processing voice input.")

    async def synthesize(self, text: str, language_code: str = "en", speaker_gender: str = "female") -> SynthesisResult:
        """
        Synthesizes text into high-fidelity speech audio bytes via Sarvam bulbul TTS.
        """
        if not self._api_key or self._api_key.startswith("your_"):
            raise VoiceProcessingException("SARVAM_API_KEY is not configured on the server.")

        clean_text = text.strip()
        if not clean_text:
            raise VoiceProcessingException("Cannot synthesize speech from empty text.")

        # Strip markdown syntax and brackets that don't sound natural when spoken
        import re
        clean_text = re.sub(r"\[.*?\](?:\(.*?\))?", "", clean_text)
        clean_text = re.sub(r"[*#_`~•⚠️]", "", clean_text).strip()
        if not clean_text:
            clean_text = text.strip()[:480]

        # Sarvam bulbul TTS strictly enforces max 500 characters per input element
        if len(clean_text) > 480:
            sub = clean_text[:480]
            # Try to break at punctuation: . ! ? \n
            last_break = max(sub.rfind('.'), sub.rfind('!'), sub.rfind('?'), sub.rfind('\n'))
            if last_break > 150:
                clean_text = sub[:last_break + 1].strip()
            else:
                last_space = sub.rfind(' ')
                if last_space > 100:
                    clean_text = sub[:last_space].strip() + "..."
                else:
                    clean_text = sub.strip() + "..."

        headers = {
            "api-subscription-key": self._api_key,
            "Content-Type": "application/json",
        }

        sarvam_lang = self.get_sarvam_language_tag(language_code)
        speaker = self.get_speaker(language_code, speaker_gender)

        payload = {
            "inputs": [clean_text],
            "target_language_code": sarvam_lang,
            "speaker": speaker,
            "model": self.tts_model,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.tts_url, headers=headers, json=payload)

                if response.status_code == 401 or response.status_code == 403:
                    logger.error("Sarvam TTS authentication failed (401/403).")
                    raise VoiceProcessingException("Sarvam TTS provider authentication error. Please verify server credentials.", status_code=status.HTTP_502_BAD_GATEWAY)

                if response.status_code == 402:
                    logger.warning("Sarvam TTS quota/credits exhausted (402).")
                    raise VoiceProcessingException("Sarvam AI voice synthesis credits exhausted (HTTP 402). Please check account credits.", status_code=status.HTTP_402_PAYMENT_REQUIRED)

                if response.status_code == 429:
                    logger.warning("Sarvam TTS rate limit exceeded (429).")
                    raise VoiceProcessingException("Voice synthesis rate limit reached. Please retry in a moment.", status_code=status.HTTP_429_TOO_MANY_REQUESTS)

                if response.status_code != 200:
                    err_msg = "Voice synthesis encountered an error."
                    try:
                        err_body = response.json()
                        if isinstance(err_body, dict) and "error" in err_body:
                            api_msg = err_body["error"].get("message") if isinstance(err_body["error"], dict) else str(err_body["error"])
                            if api_msg:
                                err_msg = f"Voice synthesis error: {api_msg}"
                    except Exception:
                        pass
                    logger.error(f"Sarvam TTS returned HTTP {response.status_code}: {err_msg}")
                    raise VoiceProcessingException(err_msg, status_code=response.status_code if 400 <= response.status_code < 600 else status.HTTP_502_BAD_GATEWAY)

                result = response.json()
                audios = result.get("audios", [])
                if not audios or not audios[0]:
                    raise VoiceProcessingException("Voice service returned empty audio data.", status_code=status.HTTP_502_BAD_GATEWAY)

                try:
                    audio_data = base64.b64decode(audios[0])
                except Exception:
                    raise VoiceProcessingException("Malformed audio payload received from voice service.", status_code=status.HTTP_502_BAD_GATEWAY)

                return SynthesisResult(
                    audio_bytes=audio_data,
                    content_type="audio/wav",
                    provider="sarvam"
                )

        except httpx.TimeoutException:
            logger.warning("Sarvam TTS request timed out.")
            raise VoiceProcessingException("Voice synthesis timed out.", status_code=status.HTTP_504_GATEWAY_TIMEOUT)
        except httpx.RequestError as exc:
            logger.error(f"Network error calling Sarvam TTS: {type(exc).__name__}")
            raise VoiceProcessingException("Unable to connect to speech synthesis service.", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        except VoiceProcessingException:
            raise
        except Exception as exc:
            logger.error(f"Unexpected error in Sarvam TTS: {type(exc).__name__}")
            raise VoiceProcessingException("Unexpected error during speech synthesis.")

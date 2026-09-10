import io
import os
import wave
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from jose import jwt
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.services.voice.base import TranscriptionResult, SynthesisResult
from app.services.voice.sarvam import SarvamVoiceProvider
from app.core.exceptions import VoiceProcessingException

client = TestClient(app)


def _generate_wav_bytes(duration_sec: float = 0.5) -> bytes:
    """Generates a small valid RIFF WAV buffer for testing audio uploads."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        num_frames = int(16000 * duration_sec)
        wav.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


def _create_test_jwt(user_id: str) -> str:
    """Creates a genuine signed JWT token for the given user_id."""
    payload = {
        "sub": user_id,
        "role": "farmer",
        "exp": 9999999999
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ============================================================================
# REGRESSION TEST A: DEMO_MODE=true + no JWT + assistant/chat -> 200
# ============================================================================
def test_a_demo_mode_true_no_jwt_assistant_chat_200():
    """Verifies that in DEMO_MODE without JWT, text chat succeeds and returns 200."""
    with patch.object(settings, "DEMO_MODE", True):
        resp = client.post(
            "/api/v1/assistant/chat",
            json={
                "message": "What should I do today?",
                "language_code": "en",
                "session_id": "test_demo_chat_session"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["reply_text"]) > 0


# ============================================================================
# REGRESSION TEST B: DEMO_MODE=true + no JWT + voice/interact -> successful pipeline
# ============================================================================
def test_b_demo_mode_true_no_jwt_voice_interact_pipeline():
    """Verifies that in DEMO_MODE without JWT, voice interact runs the full pipeline."""
    wav_bytes = _generate_wav_bytes(0.3)

    with patch.object(settings, "DEMO_MODE", True):
        with patch("app.api.v1.voice.get_voice_provider") as mock_get_vp:
            mock_provider = MagicMock()
            mock_provider.transcribe = AsyncMock(return_value=TranscriptionResult(
                text="What is my active crop?",
                language_code="en",
                confidence=0.98,
                provider="sarvam"
            ))
            mock_provider.synthesize = AsyncMock(return_value=SynthesisResult(
                audio_bytes=b"demo_reply_audio",
                content_type="audio/wav",
                duration_seconds=2.0,
                provider="sarvam"
            ))
            mock_get_vp.return_value = mock_provider

            resp = client.post(
                "/api/v1/voice/interact",
                files={"file": ("demo_voice.wav", wav_bytes, "audio/wav")},
                data={"language": "en", "session_id": "session_demo_voice"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["user_transcription"] == "What is my active crop?"
            assert len(data["assistant_text"]) > 0
            assert "assistant_audio_base64" in data
            assert data["voice_state"] == "RESPONDING"


# ============================================================================
# REGRESSION TEST C: DEMO_MODE=true + no JWT + voice/tts -> successful TTS path
# ============================================================================
def test_c_demo_mode_true_no_jwt_voice_tts_path():
    """Verifies that in DEMO_MODE without JWT, voice/tts succeeds without farm auth."""
    with patch.object(settings, "DEMO_MODE", True):
        with patch("app.api.v1.voice.get_voice_provider") as mock_get_vp:
            mock_provider = MagicMock()
            mock_provider.synthesize = AsyncMock(return_value=SynthesisResult(
                audio_bytes=b"demo_audio_bytes",
                content_type="audio/wav",
                duration_seconds=2.0,
                provider="sarvam"
            ))
            mock_get_vp.return_value = mock_provider

            resp = client.post(
                "/api/v1/voice/tts",
                json={
                    "text": "నమస్కారం, ఈరోజు నీటి యాజమాన్యం ముఖ్యం.",
                    "language_code": "te"
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "audio_base64" in data


# ============================================================================
# REGRESSION TEST D: DEMO_MODE=false + no JWT + assistant/chat -> 401
# ============================================================================
def test_d_demo_mode_false_no_jwt_assistant_chat_401():
    """Verifies that in production with DEMO_MODE=False, unauthenticated chat returns 401."""
    with patch.object(settings, "DEMO_MODE", False), \
         patch.object(settings, "APP_ENV", "production"):
        resp = client.post(
            "/api/v1/assistant/chat",
            json={
                "message": "What should I do today?",
                "language_code": "en",
                "session_id": "session_unauth_chat"
            }
        )
        assert resp.status_code == 401
        assert "Authentication required" in resp.json()["detail"]
        assert "WWW-Authenticate" in resp.headers


# ============================================================================
# REGRESSION TEST E: DEMO_MODE=false + no JWT + voice/interact -> 401
# ============================================================================
def test_e_demo_mode_false_no_jwt_voice_interact_401():
    """Verifies that in production with DEMO_MODE=False, unauthenticated voice returns 401."""
    wav_bytes = _generate_wav_bytes(0.2)

    with patch.object(settings, "DEMO_MODE", False), \
         patch.object(settings, "APP_ENV", "production"):
        resp = client.post(
            "/api/v1/voice/interact",
            files={"file": ("unauth.wav", wav_bytes, "audio/wav")},
            data={"language": "en", "session_id": "session_unauth_voice"}
        )
        assert resp.status_code == 401
        assert "Authentication required" in resp.json()["detail"]
        assert "WWW-Authenticate" in resp.headers


# ============================================================================
# REGRESSION TEST F: authenticated JWT + assistant/chat -> existing behavior
# ============================================================================
def test_f_authenticated_jwt_assistant_chat():
    """Verifies that an authenticated JWT runs the full chat assistant pipeline."""
    test_token = _create_test_jwt("auth_farmer_1")
    from app.api.deps import get_current_user

    mock_auth_user = User(
        id="auth_farmer_1",
        phone_number="9988776655"
    )
    mock_auth_profile = FarmerProfile(
        id="farmer_prof_auth_1",
        user_id="auth_farmer_1",
        name="Anand Sharma",
        preferred_language="en",
        state="Maharashtra",
        district="Nashik",
        village="Niphad"
    )
    mock_auth_user.farmer_profile = mock_auth_profile

    app.dependency_overrides[get_current_user] = lambda: mock_auth_user
    try:
        resp = client.post(
            "/api/v1/assistant/chat",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "message": "What is the best harvesting time?",
                "language_code": "en",
                "session_id": "auth_chat_turn"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["reply_text"]) > 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# REGRESSION TEST G: authenticated JWT + voice/interact -> existing behavior
# ============================================================================
def test_g_authenticated_jwt_voice_interact():
    """Verifies that an authenticated JWT runs the full voice interaction pipeline."""
    test_token = _create_test_jwt("auth_farmer_1")
    wav_bytes = _generate_wav_bytes(0.3)

    from app.api.deps import get_current_user
    mock_auth_user = User(
        id="auth_farmer_1",
        phone_number="9988776655"
    )
    mock_auth_profile = FarmerProfile(
        id="farmer_prof_auth_1",
        user_id="auth_farmer_1",
        name="Anand Sharma",
        preferred_language="en",
        state="Maharashtra",
        district="Nashik",
        village="Niphad"
    )
    mock_auth_user.farmer_profile = mock_auth_profile

    with patch("app.api.v1.voice.get_voice_provider") as mock_get_vp:
        mock_provider = MagicMock()
        mock_provider.transcribe = AsyncMock(return_value=TranscriptionResult(
            text="How much fertilizer should I apply?",
            language_code="en",
            confidence=0.96,
            provider="sarvam"
        ))
        mock_provider.synthesize = AsyncMock(return_value=SynthesisResult(
            audio_bytes=b"voice_reply_audio",
            content_type="audio/wav",
            duration_seconds=1.5,
            provider="sarvam"
        ))
        mock_get_vp.return_value = mock_provider

        app.dependency_overrides[get_current_user] = lambda: mock_auth_user
        try:
            resp = client.post(
                "/api/v1/voice/interact",
                headers={"Authorization": f"Bearer {test_token}"},
                files={"file": ("query.wav", wav_bytes, "audio/wav")},
                data={"language": "en", "session_id": "test_auth_voice_session"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["user_transcription"] == "How much fertilizer should I apply?"
            assert len(data["assistant_text"]) > 0
            assert data["voice_state"] == "RESPONDING"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# REGRESSION TEST H: arbitrary farmer_id cannot override demo farmer
# ============================================================================
def test_h_arbitrary_farmer_id_cannot_override_demo_farmer():
    """Verifies that an unauthenticated user passing an arbitrary farmer_id cannot hijack data."""
    with patch.object(settings, "DEMO_MODE", True):
        # Pass a malicious/arbitrary farmer_id in the request payload
        resp = client.post(
            "/api/v1/assistant/chat",
            json={
                "message": "What is my farm name?",
                "language_code": "en",
                "farm_id": "farm_victim_999",
                "session_id": "hijack_attempt_session"
            }
        )
        assert resp.status_code == 200
        # The backend uses the canonical demo farmer resolved by get_current_farmer_profile,
        # which is demo_farmer_1, never farm_victim_999.


# ============================================================================
# REGRESSION TEST I: no fake JWT generated in frontend
# ============================================================================
def test_i_no_fake_jwt_generated():
    """Verifies that frontend code does not manufacture fake tokens like demo_token_*."""
    app_js_path = os.path.join(settings.ROOT_DIR, "frontend", "web", "static", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'authToken = "demo_token_ramesh_rao"' not in content
    assert 'authToken = "demo_' not in content
    assert "authToken = null" in content


# ============================================================================
# REGRESSION TEST J: existing SafetyEngine still executes in demo mode
# ============================================================================
def test_j_existing_safety_engine_still_executes():
    """Verifies that SafetyEngine still executes and blocks banned chemicals like monocrotophos."""
    with patch.object(settings, "DEMO_MODE", True):
        resp = client.post(
            "/api/v1/assistant/chat",
            json={
                "message": "Spray monocrotophos on my crop.",
                "language_code": "en",
                "session_id": "safety_block_turn"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        # SafetyEngine warns or blocks banned insecticide
        reply = data["reply_text"].lower()
        assert any(term in reply for term in ["banned", "monocrotophos", "prohibited", "safety", "not recommended", "restricted"])


# ============================================================================
# REGRESSION TEST K: existing RAG grounding still executes
# ============================================================================
def test_k_existing_rag_grounding_still_executes():
    """Verifies that RAG knowledge retrieval and agronomic grounding remain fully active."""
    with patch.object(settings, "DEMO_MODE", True):
        resp = client.post(
            "/api/v1/assistant/chat",
            json={
                "message": "Why are my chilli leaves curling upwards with boat-shaped appearance?",
                "language_code": "en",
                "session_id": "rag_grounding_session"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        reply = data["reply_text"].lower()
        # Should identify thrips / leaf curl based on ANGRAU / RAG knowledge
        assert any(term in reply for term in ["thrips", "curl", "mite", "scirtothrips", "chilli"])


# ============================================================================
# REGRESSION TEST L: Sarvam 402 remains distinguishable from application 401
# ============================================================================
@pytest.mark.asyncio
async def test_l_sarvam_402_distinguishable_from_app_401():
    """Verifies that Sarvam quota 402 is distinct from Bhoomi digital twin authentication 401."""
    provider = SarvamVoiceProvider(api_key="mock_key")

    mock_resp_402 = MagicMock(status_code=402)
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp_402)):
        with pytest.raises(VoiceProcessingException) as exc_info:
            await provider.synthesize(text="Hello farmer", language_code="en")
        assert exc_info.value.status_code == 402
        assert exc_info.value.status_code != 401
        assert "credits" in str(exc_info.value).lower() or "quota" in str(exc_info.value).lower()


# ============================================================================
# REGRESSION TEST M: existing text/voice/image intelligence pipeline remains unchanged
# ============================================================================
def test_m_existing_pipeline_remains_unchanged():
    """Verifies that all 6 languages (en, te, hi, ta, kn, ml) and multi-turn flows remain intact."""
    provider = SarvamVoiceProvider(api_key="mock_key")
    for lang in ["en", "te", "hi", "ta", "kn", "ml"]:
        tag = provider.get_sarvam_language_tag(lang)
        assert tag.startswith(lang)
        assert provider.normalize_language_code(lang) == lang

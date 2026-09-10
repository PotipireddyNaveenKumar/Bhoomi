import pytest
import io
import wave
import struct
from fastapi.testclient import TestClient
from sqlalchemy.future import select

from app.main import app
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.models.farm import Farm
from app.models.crop import FarmCrop
from app.models.chat import ChatSession, ChatMessage
from app.services.demo.demo_service import DemoModeService

client = TestClient(app)


def generate_dummy_wav() -> bytes:
    """Generate a minimal valid 16kHz mono PCM WAV for audio testing."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        frames = struct.pack("<500h", *([0] * 500))
        wf.writeframes(frames)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def reset_demo_state():
    DemoModeService.reset_demo_state()
    yield
    DemoModeService.reset_demo_state()


class TestRailwayForensicFixes:
    """
    Forensic verification for the 5 public Railway deployment issues.
    """

    @pytest.mark.asyncio
    async def test_canonical_demo_data_seeding_idempotent(self):
        """Verify ensure_canonical_demo_data seeds all required tables idempotently."""
        async with AsyncSessionLocal() as db:
            # Seed 1
            await DemoModeService.ensure_canonical_demo_data(db)
            # Seed 2 (should not fail or duplicate)
            await DemoModeService.ensure_canonical_demo_data(db)

            # Check User
            res_user = await db.execute(select(User).where(User.id == "demo_user_1"))
            user = res_user.scalars().first()
            assert user is not None
            assert user.phone_number == "+919876543210"

            # Check FarmerProfile
            res_prof = await db.execute(select(FarmerProfile).where(FarmerProfile.id == "demo_farmer_1"))
            prof = res_prof.scalars().first()
            assert prof is not None
            assert prof.name == "Ramesh Kumar (Demo Farmer)"
            assert prof.district == "Guntur"

            # Check Farm
            res_farm = await db.execute(select(Farm).where(Farm.id == "farm_demo_1"))
            farm = res_farm.scalars().first()
            assert farm is not None
            assert farm.farmer_id == prof.id
            assert farm.soil_type == "black"

            # Check Crop
            res_crop = await db.execute(select(FarmCrop).where(FarmCrop.id == "crop_demo_1"))
            crop = res_crop.scalars().first()
            assert crop is not None
            assert crop.farm_id == farm.id
            assert crop.crop_name == "Chilli"

    def test_otp_send_and_verify_success(self):
        """Issue 1: Test OTP send and successful verification with farmer registration."""
        phone = "9876543211"
        res_send = client.post("/api/v1/auth/send-otp", json={"phone_number": phone})
        assert res_send.status_code == 200
        send_data = res_send.json()
        otp = send_data.get("otp") or send_data.get("demo_otp")
        assert otp is not None

        # Verify OTP
        res_verify = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": phone,
            "otp": otp,
            "full_name": "Test Farmer",
            "preferred_language": "te",
            "state": "Andhra Pradesh",
            "district": "Guntur",
            "current_crop": "Chilli",
            "land_area_acres": 3.0,
            "soil_n": 90.0,
            "soil_p": 42.0,
            "soil_k": 43.0,
            "soil_ph": 6.5
        })
        assert res_verify.status_code == 200
        verify_data = res_verify.json()
        assert "access_token" in verify_data
        assert verify_data["token_type"] == "bearer"
        assert verify_data["name"] == "Test Farmer"

    def test_otp_verify_invalid_code(self):
        """Issue 1: Test OTP verification with invalid code returns 400 Bad Request."""
        res = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": "9876543211",
            "otp": "8888",
            "full_name": "Test Farmer"
        })
        assert res.status_code == 400
        data = res.json()
        assert "detail" in data
        assert "Invalid" in data["detail"] or "expired" in data["detail"]

    def test_assistant_feedback_demo_mode(self, monkeypatch):
        """Issue 2: Test assistant feedback succeeds under DEMO_MODE and records trace."""
        monkeypatch.setattr(settings, "DEMO_MODE", True)

        res = client.post("/api/v1/assistant/feedback", json={
            "session_id": "session_feedback_test",
            "rating": "helpful",
            "response_text": "Apply neem oil for aphid management on Chilli.",
            "language_code": "en"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["rating"] == "helpful"

    def test_kharif_crop_highest_net_profit_query(self, monkeypatch):
        """Issue 3: Test 'Which Kharif crop will yield highest net profit for 3 acres of black soil?' executes real pipeline."""
        monkeypatch.setattr(settings, "DEMO_MODE", True)

        query = "Which Kharif crop will yield highest net profit for 3 acres of black soil?"
        res = client.post("/api/v1/assistant/chat", json={
            "message": query,
            "session_id": "session_kharif_profit_test",
            "language_code": "en"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["reply_text"]) > 20
        # Ensure it contains economic/cultivation reasoning
        reply_lower = data["reply_text"].lower()
        assert any(term in reply_lower for term in ["profit", "acres", "yield", "revenue", "cost", "chilli", "black"])
        # Ensure visual cards were generated
        assert len(data["visual_cards"]) >= 1

    def test_voice_interact_demo_mode_success(self, monkeypatch):
        """Issue 4 & 5: Test voice interaction endpoint succeeds and returns structured response."""
        monkeypatch.setattr(settings, "DEMO_MODE", True)

        wav_bytes = generate_dummy_wav()
        res = client.post(
            "/api/v1/voice/interact",
            files={"file": ("test_voice.wav", wav_bytes, "audio/wav")},
            data={"language": "en", "session_id": "session_voice_test"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "user_transcription" in data
        assert "assistant_text" in data
        assert "session_id" in data
        assert data["voice_state"] == "RESPONDING"

    def test_multilingual_chat_responses(self, monkeypatch):
        """Issue 3 / Multilingual: Verify Telugu and Hindi responses."""
        monkeypatch.setattr(settings, "DEMO_MODE", True)

        # Telugu query
        res_te = client.post("/api/v1/assistant/chat", json={
            "message": "నల్లరేగడి నేలలో ఏ పంట వేస్తే ఎక్కువ లాభం వస్తుంది?",
            "session_id": "session_lang_te",
            "language_code": "te"
        })
        assert res_te.status_code == 200
        data_te = res_te.json()
        assert len(data_te["reply_text"]) > 10
        assert data_te["language_code"] == "te"

        # Hindi query
        res_hi = client.post("/api/v1/assistant/chat", json={
            "message": "काली मिट्टी में कौन सी फसल सबसे अधिक मुनाफा देगी?",
            "session_id": "session_lang_hi",
            "language_code": "hi"
        })
        assert res_hi.status_code == 200
        data_hi = res_hi.json()
        assert len(data_hi["reply_text"]) > 10
        assert data_hi["language_code"] == "hi"

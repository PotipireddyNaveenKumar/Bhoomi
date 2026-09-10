import pytest
import io
import wave
import struct
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.datetime_utils import utc_now_naive, ensure_utc_naive, NaiveUTCDateTime
from app.db.session import AsyncSessionLocal
from app.models.chat import ChatSession, ChatMessage
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.models.farm import Farm
from app.models.crop import FarmCrop
from app.models.task import FarmTask
from app.models.memory import FarmerMemory
from app.models.prediction import PredictionHistory
from app.repositories.chat_repo import ChatRepository
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
def reset_demo():
    DemoModeService.reset_demo_state()
    yield
    DemoModeService.reset_demo_state()


class TestNeonPostgresDatetimePolicy:
    """
    Regression test suite verifying canonical offset-naive UTC datetime policy
    across SQLAlchemy models, asyncpg query binding, and database repositories.
    """

    def test_datetime_utils_utc_now_naive(self):
        """Verify utc_now_naive produces offset-naive UTC timestamps."""
        now = utc_now_naive()
        assert isinstance(now, datetime)
        assert now.tzinfo is None

        # Verify it represents UTC (close to datetime.now(timezone.utc))
        utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
        assert abs((now - utc_now).total_seconds()) < 2.0

    def test_ensure_utc_naive_conversion(self):
        """Verify ensure_utc_naive correctly strips tzinfo after converting to UTC."""
        # Aware UTC
        aware_utc = datetime.now(timezone.utc)
        naive_converted = ensure_utc_naive(aware_utc)
        assert naive_converted.tzinfo is None
        assert abs((aware_utc.replace(tzinfo=None) - naive_converted).total_seconds()) < 0.001

        # Aware non-UTC (+5:30 IST)
        ist = timezone(timedelta(hours=5, minutes=30))
        aware_ist = datetime(2026, 9, 11, 10, 0, 0, tzinfo=ist)
        naive_from_ist = ensure_utc_naive(aware_ist)
        assert naive_from_ist.tzinfo is None
        # 10:00 IST = 04:30 UTC
        assert naive_from_ist.hour == 4
        assert naive_from_ist.minute == 30

        # Already naive
        naive_orig = datetime(2026, 9, 11, 4, 30, 0)
        assert ensure_utc_naive(naive_orig) == naive_orig
        assert ensure_utc_naive(None) is None

    def test_naive_utc_datetime_type_decorator(self):
        """Verify NaiveUTCDateTime process_bind_param converts aware to naive UTC."""
        decorator = NaiveUTCDateTime()
        aware_dt = datetime.now(timezone.utc)
        bind_val = decorator.process_bind_param(aware_dt, None)
        assert isinstance(bind_val, datetime)
        assert bind_val.tzinfo is None

    @pytest.mark.asyncio
    async def test_chat_session_naive_utc_insertion(self):
        """Phase 3: Verify ChatRepository.get_or_create_session creates naive UTC timestamps."""
        async with AsyncSessionLocal() as db:
            await DemoModeService.ensure_canonical_demo_data(db)
            chat_repo = ChatRepository(db)

            session = await chat_repo.get_or_create_session(
                farmer_id="demo_farmer_1",
                session_id="test_sess_dt_1",
                language="te"
            )
            assert session is not None
            assert session.id == "test_sess_dt_1"
            assert session.created_at is not None
            assert session.created_at.tzinfo is None
            assert session.updated_at is not None
            assert session.updated_at.tzinfo is None

    @pytest.mark.asyncio
    async def test_chat_message_naive_utc_insertion(self):
        """Phase 3 & 7: Verify ChatRepository.save_message creates naive UTC timestamps and updates session."""
        async with AsyncSessionLocal() as db:
            await DemoModeService.ensure_canonical_demo_data(db)
            chat_repo = ChatRepository(db)

            session = await chat_repo.get_or_create_session(
                farmer_id="demo_farmer_1",
                session_id="test_sess_dt_2",
                language="en"
            )

            msg = await chat_repo.save_message(
                session_id=session.id,
                sender="user",
                content="What is the fertilizer schedule for chilli?",
                input_mode="text"
            )
            assert msg is not None
            assert msg.created_at is not None
            assert msg.created_at.tzinfo is None

            # Re-fetch session to verify updated_at is naive UTC
            res = await db.execute(select(ChatSession).where(ChatSession.id == session.id))
            refreshed_sess = res.scalars().first()
            assert refreshed_sess.updated_at is not None
            assert refreshed_sess.updated_at.tzinfo is None

    @pytest.mark.asyncio
    async def test_all_models_bind_naive_utc(self):
        """Phase 8: Verify all 9 database models bind naive UTC to TIMESTAMP columns."""
        decorator = NaiveUTCDateTime()
        aware_now = datetime.now(timezone.utc)

        # 1. User
        u = User(phone_number="+919111111111", hashed_password="pw", created_at=aware_now)
        assert decorator.process_bind_param(u.created_at, None).tzinfo is None

        # 2. FarmerProfile
        fp = FarmerProfile(user_id="u1", name="F", created_at=aware_now, updated_at=aware_now)
        assert decorator.process_bind_param(fp.created_at, None).tzinfo is None
        assert decorator.process_bind_param(fp.updated_at, None).tzinfo is None

        # 3. Farm
        f = Farm(farmer_id="f1", total_area_acres=3.0, created_at=aware_now)
        assert decorator.process_bind_param(f.created_at, None).tzinfo is None

        # 4. FarmCrop
        c = FarmCrop(farm_id="f1", crop_name="Chilli", area_acres=3.0, created_at=aware_now)
        assert decorator.process_bind_param(c.created_at, None).tzinfo is None

        # 5. FarmTask
        t = FarmTask(farmer_id="f1", farm_id="fa1", title="T", due_date=datetime.now().date(), created_at=aware_now)
        assert decorator.process_bind_param(t.created_at, None).tzinfo is None

        # 6. FarmerMemory
        m = FarmerMemory(farmer_id="f1", key="k", value="v", created_at=aware_now)
        assert decorator.process_bind_param(m.created_at, None).tzinfo is None

        # 7. PredictionHistory
        p = PredictionHistory(farmer_id="f1", prediction_type="yield", input_features={}, output_result={}, created_at=aware_now)
        assert decorator.process_bind_param(p.created_at, None).tzinfo is None

        # 8. ChatSession
        cs = ChatSession(farmer_id="f1", created_at=aware_now, updated_at=aware_now)
        assert decorator.process_bind_param(cs.created_at, None).tzinfo is None

        # 9. ChatMessage
        cm = ChatMessage(session_id="s1", sender="user", content="hello", created_at=aware_now)
        assert decorator.process_bind_param(cm.created_at, None).tzinfo is None

    def test_voice_interact_session_creation_and_persistence(self, monkeypatch):
        """Phase 4 & 5: Verify POST /api/v1/voice/interact creates session & persists voice turn with same session_id."""
        monkeypatch.setattr(settings, "DEMO_MODE", True)

        wav_bytes = generate_dummy_wav()
        test_session_id = "voice_session_persistence_test"

        res = client.post(
            "/api/v1/voice/interact",
            files={"file": ("farmer_query.wav", wav_bytes, "audio/wav")},
            data={"language": "en", "session_id": test_session_id}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == test_session_id
        assert "user_transcription" in data
        assert "assistant_text" in data
        assert data["voice_state"] == "RESPONDING"

    def test_assistant_chat_persistence_success(self, monkeypatch):
        """Phase 7: Verify POST /api/v1/assistant/chat persists conversation turn without error."""
        monkeypatch.setattr(settings, "DEMO_MODE", True)

        test_session_id = "chat_session_persistence_test"
        res = client.post("/api/v1/assistant/chat", json={
            "message": "What is the recommended seed rate for Teja chilli?",
            "session_id": test_session_id,
            "language_code": "en"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == test_session_id
        assert len(data["reply_text"]) > 10

    def test_feedback_persistence_success(self, monkeypatch):
        """Phase 6: Verify POST /api/v1/assistant/feedback succeeds for the persisted session."""
        monkeypatch.setattr(settings, "DEMO_MODE", True)

        test_session_id = "chat_session_persistence_test"
        res = client.post("/api/v1/assistant/feedback", json={
            "session_id": test_session_id,
            "rating": "helpful",
            "response_text": "Recommended seed rate for Teja chilli is 1.0 - 1.5 kg per acre.",
            "language_code": "en"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["rating"] == "helpful"

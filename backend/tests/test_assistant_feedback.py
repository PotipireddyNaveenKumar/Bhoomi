import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import AsyncSessionLocal
from app.models.farmer import FarmerProfile
from app.models.chat import ChatSession, ChatMessage
from app.repositories.chat_repo import ChatRepository
from app.services.farm_manager.recommendation_trace import RecommendationTraceStore, RecommendationRecord, FeedbackStatus
from app.services.memory.farm_memory_v2 import FarmMemoryV2, MemoryEntry
from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.services.demo.demo_service import DemoModeService
from app.services.safety.safety_engine import SafetyEngine

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    DemoModeService.reset_demo_state()
    yield
    DemoModeService.reset_demo_state()


class TestAssistantFeedbackAndOrchestrator:
    """
    Focused regression tests for Assistant Feedback Endpoint & Multilingual Orchestrator behavior.
    """

    def test_feedback_helpful_success(self):
        """1. POST /api/v1/assistant/feedback with helpful returns success."""
        res = client.post("/api/v1/assistant/feedback", json={
            "session_id": "test_session_1",
            "rating": "helpful",
            "response_text": "Apply neem oil 10000 ppm @ 2ml/L.",
            "language_code": "en"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["rating"] == "helpful"

    def test_feedback_not_helpful_success(self):
        """2. POST /api/v1/assistant/feedback with not_helpful returns success."""
        res = client.post("/api/v1/assistant/feedback", json={
            "session_id": "test_session_1",
            "rating": "not_helpful",
            "response_text": "Hold Chilli stock for 30 days.",
            "language_code": "te"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["rating"] == "not_helpful"

    def test_feedback_invalid_rating_rejected(self):
        """3. Invalid rating is rejected with HTTP 400."""
        res = client.post("/api/v1/assistant/feedback", json={
            "session_id": "test_session_1",
            "rating": "invalid_rating",
            "response_text": "Sample text",
            "language_code": "en"
        })
        assert res.status_code == 400
        assert "Invalid rating" in res.json()["detail"]

    def test_feedback_invalid_payload_rejected(self):
        """4. Malformed payload missing required rating is rejected with HTTP 422."""
        res = client.post("/api/v1/assistant/feedback", json={
            "session_id": "test_session_1"
            # rating is omitted
        })
        assert res.status_code == 422

    def test_feedback_invalid_language_rejected(self):
        """Invalid language_code is rejected with HTTP 400."""
        res = client.post("/api/v1/assistant/feedback", json={
            "session_id": "test_session_1",
            "rating": "helpful",
            "language_code": "unsupported_lang_xyz"
        })
        assert res.status_code == 400
        assert "Invalid language_code" in res.json()["detail"]

    @pytest.mark.asyncio
    async def test_feedback_recorded_in_trace_and_memory(self):
        """5. Feedback is recorded in RecommendationTraceStore and FarmMemoryV2."""
        farmer_id = DemoModeService.DEMO_FARMER_ID
        trace_id = "rec_test_trace_1"

        # Pre-seed a recommendation trace for this farmer
        RecommendationTraceStore.record_trace(RecommendationRecord(
            recommendation_id=trace_id,
            farmer_id=farmer_id,
            farm_id="farm_1",
            intent="PEST_MANAGEMENT",
            recommendation_text="Install yellow sticky traps.",
            confidence=0.9
        ))

        res = client.post("/api/v1/assistant/feedback", json={
            "session_id": "session_feedback_test",
            "rating": "helpful",
            "response_text": "Install yellow sticky traps.",
            "language_code": "en"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["trace_updated"] is True
        assert data["memory_recorded"] is True

        # Verify trace record was updated
        trace = RecommendationTraceStore.get_trace(trace_id)
        assert trace is not None
        assert trace.feedback_rating == FeedbackStatus.HELPFUL
        assert trace.farmer_action == FeedbackStatus.FOLLOWED

        # Verify FarmMemoryV2 episodic entry exists
        memories = FarmMemoryV2.get_memories_by_category(farmer_id, "FEEDBACK")
        assert len(memories) >= 1
        assert any(m.value.get("rating") == "helpful" for m in memories)

    def test_existing_manager_feedback_remains_intact(self):
        """7. Existing manager feedback endpoint (POST /api/v1/manager/feedback) works unchanged."""
        trace_id = "rec_manager_test_1"
        RecommendationTraceStore.record_trace(RecommendationRecord(
            recommendation_id=trace_id,
            farmer_id="farmer_mgr_test",
            farm_id="farm_1",
            intent="IRRIGATION_ADVISORY",
            recommendation_text="Irrigate 25mm today.",
            confidence=0.88
        ))

        res = client.post("/api/v1/manager/feedback", json={
            "recommendation_id": trace_id,
            "action_taken": "ACCEPTED",
            "feedback_rating": "USEFUL",
            "notes": "Applied irrigation successfully."
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["updated_record"]["feedback_rating"] == "USEFUL"
        assert data["updated_record"]["farmer_action"] == "ACCEPTED"

    @pytest.mark.asyncio
    async def test_telugu_colloquial_pest_query(self):
        """8. Telugu colloquial pest query returns authentic Telugu advice, never raw English."""
        turn = await BhoomiAgentOrchestrator.process_turn(
            farmer_id=DemoModeService.DEMO_FARMER_ID,
            session_id="session_te_pest",
            user_text="నా మిరప చేలో తామర పురుగు తెగులు వచ్చింది ఆకులు ముడుచుకుంటున్నాయి",
            input_mode="voice",
            language="te"
        )
        resp = turn.response_text
        assert len(resp) > 0
        # Must contain Telugu response and no untranslated English diagnosis heading
        assert "తామర" in resp or "మిరప" in resp or "ఆకులు" in resp or "అన్నా" in resp
        assert "Hello brother!" not in resp
        assert "Primary causes of chilli leaf curling:" not in resp

    @pytest.mark.asyncio
    async def test_hindi_colloquial_pest_query(self):
        """9. Hindi colloquial pest query is recognized with Hindi response."""
        turn = await BhoomiAgentOrchestrator.process_turn(
            farmer_id=DemoModeService.DEMO_FARMER_ID,
            session_id="session_hi_pest",
            user_text="मिर्च के खेत में पत्तियां मुड़ रही हैं और थ्रिप्स कीट लगे हैं",
            input_mode="voice",
            language="hi"
        )
        resp = turn.response_text
        assert len(resp) > 0
        assert "मिर्च" in resp or "पत्तियां" in resp or "थ्रिप्स" in resp or "ट्रैप" in resp
        assert "Hello brother!" not in resp

    @pytest.mark.asyncio
    async def test_leaf_curl_response_does_not_inject_unrelated_pending_task(self):
        """10. Leaf curl response does not inject unrelated pending irrigation tasks into diagnosis."""
        turn = await BhoomiAgentOrchestrator.process_turn(
            farmer_id=DemoModeService.DEMO_FARMER_ID,
            session_id="session_curl_clean",
            user_text="Why are my chilli leaves curling?",
            input_mode="text",
            language="en"
        )
        resp = turn.response_text
        assert len(resp) > 0
        # Must not have injected the old task_note_en format
        assert "Farm Context: Your pending task" not in resp

    @pytest.mark.asyncio
    async def test_safety_engine_still_executes_after_orchestrator(self):
        """11. SafetyEngine validates and blocks hazardous chemicals after orchestrator."""
        unsafe_query = "Can I spray monocrotophos or endosulfan on my tomato crop for caterpillar control?"
        turn = await BhoomiAgentOrchestrator.process_turn(
            farmer_id=DemoModeService.DEMO_FARMER_ID,
            session_id="session_safety_check",
            user_text=unsafe_query,
            input_mode="text",
            language="en"
        )
        resp = turn.response_text
        # The banned chemicals must not be recommended
        assert "monocrotophos" not in resp.lower() or "blocked" in resp.lower() or "safety alert" in resp.lower()
        # Verify SafetyEngine evaluation
        safety = SafetyEngine.evaluate(resp)
        assert safety.is_safe is True or "Safety Alert" in resp

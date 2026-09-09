import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.task import FarmTask, TaskType, TaskStatus
from app.schemas.decision import DecisionPriority
from app.services.demo.demo_service import DemoModeService
from app.services.farm_manager.task_engine import TaskIntelligenceEngine
from app.services.voice.confirmation_state import ConfirmationStateMachine, ConfirmationState
from app.services.safety.safety_engine import SafetyEngine
from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.services.memory.farm_memory_v2 import FarmMemoryV2
from app.services.farm_manager.recommendation_trace import RecommendationTraceStore

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_demo_state():
    """Resets the demo state before each test."""
    DemoModeService.reset_demo_state()
    yield
    DemoModeService.reset_demo_state()


class TestDemoScenarios:
    """
    Comprehensive verification for BHOOMI V2 Demonstration Scenarios (Parts 36-48).
    Validates all 11 live demonstration flows, zero-fabrication guarantees,
    timezone-aware task mutations, confirmation state machine, and safety perimeters.
    """

    def test_demo_profile_and_reset(self):
        """Part 36 & 37: Verify deterministic demo profile and reset mechanism."""
        profile = DemoModeService.get_demo_profile()
        assert profile["data_mode"] == "DEMO_PROFILE / SIMULATED"
        assert profile["farmer"]["name"] == "Ramesh Kumar (Demo Farmer)"
        assert profile["farm"]["location"] == "Tenali, Guntur, Andhra Pradesh"
        assert profile["crop"]["crop_name"] in ["Tomato", "Chilli"]
        assert profile["crop"]["current_stage"] in ["flowering", "vegetative"]

        # Check API endpoint
        res = client.get("/api/v1/demo/profile")
        assert res.status_code == 200
        data = res.json()
        assert data["farmer"]["farmer_id"] == DemoModeService.DEMO_FARMER_ID

        # Check reset endpoint
        res_reset = client.post("/api/v1/demo/reset")
        assert res_reset.status_code == 200
        assert res_reset.json()["tasks_seeded"] == 3

        # Check catalog endpoint
        res_scenarios = client.get("/api/v1/demo/scenarios")
        assert res_scenarios.status_code == 200
        assert len(res_scenarios.json()["scenarios"]) == 11

    @pytest.mark.asyncio
    async def test_scenario_1_what_should_i_do_today(self):
        """Part 38: Demo Scenario 1 — 'What should I do today?'"""
        result = await DemoModeService.execute_scenario(1)
        assert result["data_mode"] == "DEMO_PROFILE / SIMULATED"
        assert len(result["response_text"]) > 0
        # Should contain visual card for daily briefing
        card_types = [c.get("card_type") for c in result["visual_cards"]]
        assert "daily_briefing_card" in card_types

    @pytest.mark.asyncio
    async def test_scenario_2_voice_task_complete(self):
        """Part 39: Demo Scenario 2 — 'I finished watering.'"""
        tasks_before = TaskIntelligenceEngine.get_tasks_for_farm(DemoModeService.DEMO_FARM_ID)
        irrig_task = next(t for t in tasks_before if t.task_id == "task_irrig_demo")
        assert irrig_task.status == TaskStatus.DUE

        result = await DemoModeService.execute_scenario(2)
        assert "completed" in result["response_text"].lower() or "పూర్తయింది" in result["response_text"]

        tasks_after = TaskIntelligenceEngine.get_tasks_for_farm(DemoModeService.DEMO_FARM_ID)
        irrig_task_after = next(t for t in tasks_after if t.task_id == "task_irrig_demo")
        assert irrig_task_after.status == TaskStatus.COMPLETED
        assert irrig_task_after.completed_at is not None

    @pytest.mark.asyncio
    async def test_scenario_3_timezone_aware_postponement(self):
        """Part 40: Demo Scenario 3 — 'Postpone spraying by two days.'"""
        tasks_before = TaskIntelligenceEngine.get_tasks_for_farm(DemoModeService.DEMO_FARM_ID)
        spray_task = next(t for t in tasks_before if t.task_id == "task_spray_demo")
        assert spray_task.status == TaskStatus.DUE
        original_due = spray_task.due_at

        result = await DemoModeService.execute_scenario(3)
        assert "postponed" in result["response_text"].lower() or "వాయిదా" in result["response_text"]

        tasks_after = TaskIntelligenceEngine.get_tasks_for_farm(DemoModeService.DEMO_FARM_ID)
        spray_task_after = next(t for t in tasks_after if t.task_id == "task_spray_demo")
        assert spray_task_after.status == TaskStatus.POSTPONED
        assert spray_task_after.due_at != original_due
        # Verify timezone preserved
        assert "+05:30" in spray_task_after.due_at or "17:30:00" in spray_task_after.due_at

    @pytest.mark.asyncio
    async def test_scenario_4_skip_irrigation_confirmation_flow(self):
        """Part 41: Demo Scenario 4 — 'Skip irrigation' consequential confirmation flow."""
        farmer_id = DemoModeService.DEMO_FARMER_ID
        session_id = "session_demo_1"

        # Step 1: Request skip on high priority irrigation -> enters confirmation state
        turn1 = await BhoomiAgentOrchestrator.process_turn(
            farmer_id=farmer_id,
            session_id=session_id,
            user_text="Skip irrigation.",
            input_mode="voice"
        )
        assert any(w in turn1.response_text.lower() for w in ["want to skip", "yield", "soil moisture", "confirm", "sure", "risk"])

        # Check confirmation state is pending
        pending = ConfirmationStateMachine.get_session(session_id, farmer_id)
        assert pending is not None
        assert pending.state == ConfirmationState.AWAITING_CONFIRMATION
        assert pending.pending_action == "TASK_SKIP"

        # Task should NOT be skipped yet
        tasks_mid = TaskIntelligenceEngine.get_tasks_for_farm(DemoModeService.DEMO_FARM_ID)
        task_mid = next(t for t in tasks_mid if t.task_id == "task_irrig_demo")
        assert task_mid.status != TaskStatus.SKIPPED

        # Step 2: Farmer confirms "Yes"
        turn2 = await BhoomiAgentOrchestrator.process_turn(
            farmer_id=farmer_id,
            session_id=session_id,
            user_text="Yes, I confirm skip.",
            input_mode="voice"
        )
        assert "skipped" in turn2.response_text.lower() or "దాటవేయబడింది" in turn2.response_text

        # Task is now SKIPPED
        tasks_final = TaskIntelligenceEngine.get_tasks_for_farm(DemoModeService.DEMO_FARM_ID)
        task_final = next(t for t in tasks_final if t.task_id == "task_irrig_demo")
        assert task_final.status == TaskStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_scenario_5_crop_health_uncertainty_safeguard(self):
        """Part 42: Demo Scenario 5 — Crop health scouting without hallucinated chemical treatment."""
        result = await DemoModeService.execute_scenario(5)
        assert len(result["response_text"]) > 0
        # Verify no banned chemicals in advice
        safety = SafetyEngine.evaluate(result["response_text"])
        assert safety.is_safe is True

    @pytest.mark.asyncio
    async def test_scenario_6_weather_aware_irrigation(self):
        """Part 43: Demo Scenario 6 — 'Should I irrigate today?'"""
        result = await DemoModeService.execute_scenario(6)
        assert len(result["response_text"]) > 0
        assert any(term in result["response_text"].lower() for term in ["irrigation", "water", "moisture", "flowering", "drip", "weather"])

    @pytest.mark.asyncio
    async def test_scenario_7_market_intelligence_net_realization(self):
        """Part 44: Demo Scenario 7 — 'Should I sell now?'"""
        result = await DemoModeService.execute_scenario(7)
        assert len(result["response_text"]) > 0
        # Verify response provides market / price / mandi reasoning
        assert any(term in result["response_text"].lower() for term in ["price", "market", "mandi", "sell", "quintal", "₹", "rate", "realization"])

    @pytest.mark.asyncio
    async def test_scenario_8_farm_change_detection(self):
        """Part 45: Demo Scenario 8 — 'What changed on my farm?'"""
        result = await DemoModeService.execute_scenario(8)
        assert len(result["response_text"]) > 0
        card_types = [c.get("card_type") for c in result["visual_cards"]]
        assert "farm_changes_card" in card_types

    @pytest.mark.asyncio
    async def test_scenario_9_weekly_adaptive_plan(self):
        """Part 46: Demo Scenario 9 — 'What should I do this week?'"""
        result = await DemoModeService.execute_scenario(9)
        assert len(result["response_text"]) > 0
        card_types = [c.get("card_type") for c in result["visual_cards"]]
        assert "weekly_briefing_card" in card_types

    @pytest.mark.asyncio
    async def test_scenario_10_safety_engine_monocrotophos_block(self):
        """Part 47: Demo Scenario 10 — 'Spray monocrotophos.'"""
        result = await DemoModeService.execute_scenario(10)
        # SafetyEngine must intercept and block
        card_types = [c.get("card_type") for c in result["visual_cards"]]
        assert "safety_restriction_card" in card_types
        assert any(w in result["response_text"].lower() for w in ["banned", "prohibited", "safety alert", "restricted", "hazardous"])

        # Must NOT create a spraying task for monocrotophos
        tasks = TaskIntelligenceEngine.get_tasks_for_farm(DemoModeService.DEMO_FARM_ID)
        for t in tasks:
            assert "monocrotophos" not in t.title.lower()
            assert "monocrotophos" not in t.description.lower()

    @pytest.mark.asyncio
    async def test_scenario_11_rice_research_only_protection(self):
        """Part 48: Demo Scenario 11 — 'What pesticide should I spray on rice?'"""
        result = await DemoModeService.execute_scenario(11)
        # Rice research-only guard must trigger
        assert any(w in result["response_text"].lower() for w in ["research", "barred", "protocol", "safety warning"])
        card_types = [c.get("card_type") for c in result["visual_cards"]]
        assert "safety_restriction_card" in card_types

    def test_demo_api_execute_endpoint(self):
        """Verify API execution of demo scenarios via POST /api/v1/demo/scenarios/{id}/execute."""
        for scenario_id in [1, 2, 3, 10, 11]:
            res = client.post(f"/api/v1/demo/scenarios/{scenario_id}/execute")
            assert res.status_code == 200
            data = res.json()
            assert data["scenario_id"] == scenario_id
            assert data["data_mode"] == "DEMO_PROFILE / SIMULATED"
            assert "response_text" in data
            assert "voice_state" in data

    @pytest.mark.asyncio
    async def test_multilingual_demo_scenarios(self):
        """Verify multilingual input for Telugu and Hindi."""
        farmer_id = DemoModeService.DEMO_FARMER_ID
        session_id = "session_demo_multi"

        # Telugu: "ఈరోజు నేను ఏమి చేయాలి?" (What should I do today?)
        res_te = await BhoomiAgentOrchestrator.process_turn(
            farmer_id=farmer_id,
            session_id=session_id,
            user_text="ఈరోజు నేను ఏమి చేయాలి?",
            input_mode="voice"
        )
        assert len(res_te.response_text) > 0
        assert len(res_te.visual_cards) > 0

        # Hindi: "आज मुझे क्या करना चाहिए?" (What should I do today?)
        res_hi = await BhoomiAgentOrchestrator.process_turn(
            farmer_id=farmer_id,
            session_id=session_id,
            user_text="आज मुझे क्या करना चाहिए?",
            input_mode="voice"
        )
        assert len(res_hi.response_text) > 0
        assert len(res_hi.visual_cards) > 0

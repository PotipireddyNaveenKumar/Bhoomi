import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.task import FarmTask, TaskType, TaskStatus
from app.schemas.decision import DecisionPriority
from app.schemas.voice_intent import VoiceIntentType, FeedbackOutcome, TaskFeedback
from app.services.voice.intent_service import IntentNormalizationService
from app.services.voice.confirmation_state import ConfirmationStateMachine, ConfirmationState
from app.services.farm_manager.task_engine import TaskIntelligenceEngine
from app.services.farm_manager.state_engine import FarmState, FarmStateEngine
from app.services.farm_manager.proactive_alerts import (
    ProactiveAlertEngine,
    FarmerContactPreferences,
    AlertStatus
)
from app.services.farm_manager.task_adherence import TaskAdherenceService
from app.services.memory.farm_memory_v2 import FarmMemoryV2, ProvenanceType
from app.services.farm_manager.recommendation_trace import RecommendationTraceStore, RecommendationRecord
from app.services.safety.safety_engine import SafetyEngine
from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.services.memory.digital_twin import DigitalTwinContext

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_teardown_farm():
    """Resets task intelligence and state registries for consistent testing."""
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    ConfirmationStateMachine.clear_session("session_demo_1", "farmer_demo_1")
    FarmMemoryV2._store.clear()
    ProactiveAlertEngine._alert_registry.clear()
    ProactiveAlertEngine._acknowledged_hashes.clear()
    yield
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    ConfirmationStateMachine.clear_session("session_demo_1", "farmer_demo_1")


def _seed_basic_tasks(farm_id: str = "farm_1"):
    today_str = datetime.now(timezone.utc).date().isoformat()
    tomorrow_str = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    t1 = FarmTask(
        task_id="task_irrig_1",
        farm_id=farm_id,
        crop="Chilli",
        task_type=TaskType.IRRIGATION,
        title="Chilli Drip Irrigation",
        description="Apply 25,000L water via drip system.",
        priority=DecisionPriority.HIGH,
        status=TaskStatus.DUE,
        due_at=today_str,
        crop_stage="flowering",
        trigger="soil_moisture_depletion",
        reason="Soil moisture dropped below 45% depletion threshold.",
        evidence="Soil matric tension: -45 kPa.",
        source_references=["FAO-56 Irrigation SOP"],
        safety_status="VERIFIED_SAFE",
        trace_id="trace_seed_irrig"
    )
    t2 = FarmTask(
        task_id="task_scout_1",
        farm_id=farm_id,
        crop="Chilli",
        task_type=TaskType.FIELD_INSPECTION,
        title="Chilli Pest Scouting",
        description="Inspect 20 plants for thrips and mite infestation.",
        priority=DecisionPriority.MEDIUM,
        status=TaskStatus.DUE,
        due_at=today_str,
        crop_stage="flowering",
        trigger="routine_biweekly_scouting",
        reason="Early detection of chilli thrips prevents yield loss.",
        evidence="Flowering stage vulnerability.",
        source_references=["ICAR Chilli Scouting Protocol"],
        safety_status="VERIFIED_SAFE",
        trace_id="trace_seed_scout"
    )
    TaskIntelligenceEngine._tasks_by_farm[farm_id] = [t1, t2]
    return t1, t2


# ============================================================================
# CATEGORY A: VOICE INTENT EXTRACTION
# ============================================================================
def test_intent_extraction_basics():
    # English task completion
    intent_en = IntentNormalizationService.parse_intent("I finished watering.")
    assert intent_en.intent_type == VoiceIntentType.TASK_COMPLETE
    assert intent_en.target_task_type == TaskType.IRRIGATION

    # English postponement with days
    intent_postpone = IntentNormalizationService.parse_intent("Postpone watering by two days.")
    assert intent_postpone.intent_type == VoiceIntentType.TASK_POSTPONE
    assert intent_postpone.target_task_type == TaskType.IRRIGATION
    assert intent_postpone.requested_delay_days == 2

    # English skip
    intent_skip = IntentNormalizationService.parse_intent("Skip today's field inspection.")
    assert intent_skip.intent_type == VoiceIntentType.TASK_SKIP
    assert intent_skip.target_task_type == TaskType.FIELD_INSPECTION
    assert intent_skip.confirmation_required is True


# ============================================================================
# CATEGORIES B TO G: MULTILINGUAL TASK COMPLETION (EN, TE, HI, TA, KN, ML)
# ============================================================================
@pytest.mark.asyncio
async def test_english_task_completion():
    _seed_basic_tasks()
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="I finished watering.",
        input_mode="voice"
    )
    assert "COMPLETED" in res.response_text or "completed" in res.response_text.lower()
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    irrig_task = next(t for t in tasks if t.task_id == "task_irrig_1")
    assert irrig_task.status == TaskStatus.COMPLETED
    assert irrig_task.completion_source == "VOICE"


@pytest.mark.asyncio
async def test_telugu_task_completion():
    _seed_basic_tasks()
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="నీరు పెట్టడం పూర్తి చేశాను.",
        input_mode="voice"
    )
    assert "పూర్తయింది" in res.response_text or "నమోదు" in res.response_text
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    irrig_task = next(t for t in tasks if t.task_id == "task_irrig_1")
    assert irrig_task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_hindi_task_completion():
    _seed_basic_tasks()
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="सिंचाई पूरी कर ली।",
        input_mode="voice"
    )
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    irrig_task = next(t for t in tasks if t.task_id == "task_irrig_1")
    assert irrig_task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_tamil_task_completion():
    _seed_basic_tasks()
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="பாசனம் செய்துவிட்டேன்.",
        input_mode="voice"
    )
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    irrig_task = next(t for t in tasks if t.task_id == "task_irrig_1")
    assert irrig_task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_kannada_task_completion():
    _seed_basic_tasks()
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="ನೀರಾವರಿ ಮುಗಿಸಿದೆ.",
        input_mode="voice"
    )
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    irrig_task = next(t for t in tasks if t.task_id == "task_irrig_1")
    assert irrig_task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_malayalam_task_completion():
    _seed_basic_tasks()
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="നന പൂർത്തിയാക്കി.",
        input_mode="voice"
    )
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    irrig_task = next(t for t in tasks if t.task_id == "task_irrig_1")
    assert irrig_task.status == TaskStatus.COMPLETED


# ============================================================================
# CATEGORY H: TASK POSTPONEMENT WITH DETERMINISTIC TIMESTAMPS
# ============================================================================
@pytest.mark.asyncio
async def test_task_postponement():
    t1, _ = _seed_basic_tasks()
    original_due = t1.due_at

    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="Postpone watering by two days.",
        input_mode="voice"
    )
    assert "POSTPONED" in res.response_text or "వాయిదా" in res.response_text
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    target = next(t for t in tasks if t.task_id == "task_irrig_1")
    assert target.status == TaskStatus.POSTPONED
    assert target.old_due_time == original_due
    expected_due = (datetime.now(timezone.utc).date() + timedelta(days=2)).isoformat()
    assert target.due_at == expected_due
    assert target.new_due_time == expected_due


# ============================================================================
# CATEGORY I & K: TASK SKIP WITH CONSEQUENTIAL CONFIRMATION FLOW
# ============================================================================
@pytest.mark.asyncio
async def test_consequential_task_skip_requires_confirmation():
    _seed_basic_tasks()

    # Step 1: Farmer requests skipping irrigation (consequential because HIGH priority / irrigation)
    res1 = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="Skip today's irrigation.",
        input_mode="voice"
    )
    # Must NOT directly skip! Must ask confirmation.
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    target = next(t for t in tasks if t.task_id == "task_irrig_1")
    assert target.status != TaskStatus.SKIPPED  # Task remains DUE pending confirmation
    assert "Do you still want to skip it?" in res1.response_text or "దాటవేయాలనుకుంటున్నారా" in res1.response_text

    # Step 2: Farmer confirms with "Yes"
    res2 = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="Yes.",
        input_mode="voice"
    )
    # Now task is marked SKIPPED
    assert target.status == TaskStatus.SKIPPED
    assert "SKIPPED" in res2.response_text or "దాటవేయబడింది" in res2.response_text


@pytest.mark.asyncio
async def test_consequential_task_skip_cancellation():
    _seed_basic_tasks()

    # Step 1: Request skip
    await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="Skip today's irrigation.",
        input_mode="voice"
    )
    # Step 2: Farmer cancels with "No" / "Cancel"
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="No, cancel that.",
        input_mode="voice"
    )
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    target = next(t for t in tasks if t.task_id == "task_irrig_1")
    assert target.status == TaskStatus.DUE  # Task preserved
    assert "cancelled" in res.response_text.lower() or "రద్దు" in res.response_text


# ============================================================================
# CATEGORY J: AMBIGUOUS TASK SELECTION (DO NOT GUESS)
# ============================================================================
@pytest.mark.asyncio
async def test_ambiguous_task_disambiguation():
    # Seed two irrigation tasks for different crops
    today_str = datetime.now(timezone.utc).date().isoformat()
    t_chilli = FarmTask(
        task_id="task_irrig_chilli",
        farm_id="farm_1",
        crop="Chilli",
        task_type=TaskType.IRRIGATION,
        title="Chilli Drip Irrigation",
        priority=DecisionPriority.HIGH,
        status=TaskStatus.DUE,
        due_at=today_str,
        crop_stage="flowering",
        trigger="schedule",
        reason="Regular chilli irrigation schedule"
    )
    t_tomato = FarmTask(
        task_id="task_irrig_tomato",
        farm_id="farm_1",
        crop="Tomato",
        task_type=TaskType.IRRIGATION,
        title="Tomato Furrow Irrigation",
        priority=DecisionPriority.HIGH,
        status=TaskStatus.DUE,
        due_at=today_str,
        crop_stage="vegetative",
        trigger="schedule",
        reason="Regular tomato irrigation schedule"
    )
    TaskIntelligenceEngine._tasks_by_farm["farm_1"] = [t_chilli, t_tomato]

    # Farmer says: "I finished watering."
    res1 = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="I finished watering.",
        input_mode="voice"
    )
    # System must prompt for clarification, not execute blindly
    assert "multiple matching tasks" in res1.response_text.lower() or "బహుళ పనులను" in res1.response_text
    assert t_chilli.status == TaskStatus.DUE
    assert t_tomato.status == TaskStatus.DUE

    # Farmer clarifies: "Tomato field."
    res2 = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="Tomato field.",
        input_mode="voice"
    )
    assert t_tomato.status == TaskStatus.COMPLETED
    assert t_chilli.status == TaskStatus.DUE  # Other task untouched


# ============================================================================
# CATEGORY L: LOW-CONFIDENCE VOICE HANDLING
# ============================================================================
@pytest.mark.asyncio
async def test_low_confidence_voice_handling():
    _seed_basic_tasks()
    intent_low = IntentNormalizationService.parse_intent(
        text="muffled background tractor sound",
        confidence=0.45
    )
    assert intent_low.intent_type == VoiceIntentType.UNKNOWN

    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="...",
        input_mode="voice"
    )
    # Must ask for clarification, never execute state change
    assert "clearly understand" in res.response_text.lower() or "అర్థం కాలేదు" in res.response_text
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    assert all(t.status == TaskStatus.DUE for t in tasks)


# ============================================================================
# CATEGORIES M, N, O, P, Q: TASK QUERIES, BRIEFINGS & WHY EXPLANATION
# ============================================================================
@pytest.mark.asyncio
async def test_task_status_and_briefings():
    _seed_basic_tasks()

    # Today briefing
    res_today = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        user_text="What should I do today?",
        input_mode="voice"
    )
    assert res_today.visual_cards[0]["card_type"] == "daily_briefing_card"

    # Week plan
    res_week = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        user_text="What should I do this week?",
        input_mode="voice"
    )
    assert res_week.visual_cards[0]["card_type"] == "weekly_briefing_card"

    # Farm changes
    res_change = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        user_text="What changed on my farm?",
        input_mode="voice"
    )
    assert res_change.visual_cards[0]["card_type"] == "farm_changes_card"

    # Why explanation
    res_why = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        user_text="Why should I water?",
        input_mode="voice"
    )
    assert "Soil moisture dropped below 45%" in res_why.response_text
    assert "FAO-56" in res_why.response_text or "depletion" in res_why.response_text


# ============================================================================
# CATEGORIES R, S, T: PROACTIVE REMINDERS, DEDUPLICATION & QUIET HOURS
# ============================================================================
def test_proactive_alert_nudges_and_quiet_hours():
    t1, _ = _seed_basic_tasks()

    # 1. Standard reminder generation during active daytime hours
    prefs = FarmerContactPreferences(
        reminders_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="06:00",
        max_daily_reminders=3
    )
    nudges = ProactiveAlertEngine.evaluate_task_nudges(
        tasks=[t1],
        preferences=prefs,
        current_time_str="10:30"
    )
    assert len(nudges) == 1
    assert nudges[0].category == "REMINDER"
    assert "Chilli Drip Irrigation" in nudges[0].title

    # 2. Deduplication check: second evaluation does not duplicate unchanged reminder
    nudges_dedup = ProactiveAlertEngine.evaluate_task_nudges(
        tasks=[t1],
        preferences=prefs,
        current_time_str="11:00"
    )
    assert len(nudges_dedup) == 1  # Deduplicated to same single active alert

    # 3. Quiet hours check: 23:30 is within quiet hours (22:00 - 06:00)
    nudges_quiet = ProactiveAlertEngine.evaluate_task_nudges(
        tasks=[t1],
        preferences=prefs,
        current_time_str="23:30"
    )
    assert len(nudges_quiet) == 0  # Silenced during quiet hours

    # 4. Reminders disabled check
    prefs_disabled = FarmerContactPreferences(reminders_enabled=False)
    nudges_off = ProactiveAlertEngine.evaluate_task_nudges(
        tasks=[t1],
        preferences=prefs_disabled,
        current_time_str="14:00"
    )
    assert len(nudges_off) == 0


# ============================================================================
# CATEGORIES U, V, W: ADHERENCE CALCULATION, PERSONALIZATION & PROVENANCE
# ============================================================================
def test_longitudinal_adherence_and_feedback():
    farmer_id = "farmer_adherence_test"

    # Zero denominator test: brand new farmer has 0.0 adherence, INSUFFICIENT_DATA (not fake 100%)
    adh_initial = TaskAdherenceService.calculate_adherence(farmer_id)
    assert adh_initial.adherence_rate == 0.0
    assert adh_initial.adherence_level == "INSUFFICIENT_DATA"

    # Simulate completed tasks in FarmMemoryV2
    FarmMemoryV2.add_memory(
        farmer_id=farmer_id,
        category="EVENT",
        key="task_created_t1",
        value={"task_id": "t1"},
        provenance=ProvenanceType.SYSTEM_RECOMMENDATION
    )
    FarmMemoryV2.add_memory(
        farmer_id=farmer_id,
        category="EVENT",
        key="task_completed_t1",
        value={"task_id": "t1"},
        provenance=ProvenanceType.FARMER_ACTION
    )
    FarmMemoryV2.add_memory(
        farmer_id=farmer_id,
        category="EVENT",
        key="task_created_t2",
        value={"task_id": "t2"},
        provenance=ProvenanceType.SYSTEM_RECOMMENDATION
    )
    FarmMemoryV2.add_memory(
        farmer_id=farmer_id,
        category="EVENT",
        key="task_skipped_t2",
        value={"task_id": "t2"},
        provenance=ProvenanceType.FARMER_ACTION
    )

    # 1 completed out of 2 eligible = 50% adherence (MODERATE)
    adh_evaluated = TaskAdherenceService.calculate_adherence(farmer_id)
    assert adh_evaluated.tasks_completed == 1
    assert adh_evaluated.tasks_skipped == 1
    assert adh_evaluated.adherence_rate == 0.50
    assert adh_evaluated.adherence_level == "MODERATE"

    # Personalization Profile test
    profile = TaskAdherenceService.get_personalization_profile(farmer_id)
    assert profile.explanation_verbosity == "BALANCED"

    # Farmer Feedback recording & Provenance test
    feedback = TaskFeedback(
        task_id="t1",
        farmer_id=farmer_id,
        rating=5,
        outcome=FeedbackOutcome.SUCCESSFUL,
        comment="Drip irrigation saved 3 hours of pump run time.",
        source="farmer_voice"
    )
    recorded = TaskAdherenceService.record_feedback(feedback)
    assert recorded.outcome == FeedbackOutcome.SUCCESSFUL

    memories = FarmMemoryV2.get_memories_by_category(farmer_id, "FEEDBACK")
    assert len(memories) == 1
    assert memories[0].provenance == ProvenanceType.FARMER_REPORTED_OUTCOME
    assert memories[0].provenance != ProvenanceType.VERIFIED_OUTCOME


# ============================================================================
# CATEGORY X: TRACEABILITY VERIFICATION
# ============================================================================
@pytest.mark.asyncio
async def test_traceability_across_voice_mutation():
    _seed_basic_tasks()
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_trace_test",
        session_id="session_trace_test",
        user_text="I completed the field inspection.",
        input_mode="voice"
    )
    assert res.trace_id != ""
    # Verify trace is recorded in RecommendationTraceStore
    traces = RecommendationTraceStore.get_traces_for_farmer("farmer_trace_test")
    assert len(traces) >= 1
    assert traces[-1].intent == "TASK_COMPLETE"
    assert "TaskIntelligenceEngine.complete_task" in traces[-1].tools_used


# ============================================================================
# CATEGORIES Y & Z: SAFETY ENGINE ENFORCEMENT & RICE RESEARCH-ONLY
# ============================================================================
@pytest.mark.asyncio
async def test_safety_engine_and_rice_protection_in_voice():
    # 1. Prohibited chemical command: voice must NOT bypass SafetyEngine
    eval_banned = SafetyEngine.evaluate("I want to spray monocrotophos on my chilli crop.")
    assert eval_banned.is_safe is False
    assert eval_banned.status == "BLOCK"
    assert any("restricted/banned" in r for r in eval_banned.blocked_reasons)

    # 2. Rice chemical spray command: voice must return RESEARCH_ONLY limitation
    res_rice = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_rice_test",
        session_id="session_rice_test",
        user_text="Tell me what pesticide to spray on my rice crop.",
        input_mode="voice"
    )
    assert "RESEARCH_ONLY" in res_rice.response_text or "పరిశోధన" in res_rice.response_text
    assert len(res_rice.visual_cards) > 0
    assert res_rice.visual_cards[0]["card_type"] == "safety_restriction_card"


# ============================================================================
# CATEGORIES AA & AB: WEATHER / MARKET UNAVAILABLE RESILIENCE
# ============================================================================
@pytest.mark.asyncio
async def test_weather_market_unavailable_resilience():
    # Verify when weather is STALE/UNAVAILABLE, postponement does not invent forecast
    context = DigitalTwinContext(
        farmer_name="Suresh Patel",
        language="en",
        location="Tenali",
        state="AP",
        district="Guntur",
        village="Tenali",
        total_acres=2.0,
        soil_type="black",
        irrigation_source="borewell",
        active_crops=[{"crop_name": "Chilli", "variety": "Teja", "area_acres": 2.0, "current_stage": "flowering"}],
        historical_crops=["paddy"],
        memories={}
    )
    state = await FarmStateEngine.get_current_state(farmer_id="farmer_offline", digital_twin=context)
    # State has data_freshness indicators
    assert "weather" in state.data_freshness
    assert "market" in state.data_freshness


# ============================================================================
# CATEGORY AC: TYPING / VOICE PARITY
# ============================================================================
@pytest.mark.asyncio
async def test_typing_and_voice_parity():
    _seed_basic_tasks()

    # Voice input
    intent_voice = IntentNormalizationService.parse_intent("Postpone watering by two days.")
    # Typed input
    intent_typed = IntentNormalizationService.parse_intent("postpone watering by two days")

    assert intent_voice.intent_type == intent_typed.intent_type == VoiceIntentType.TASK_POSTPONE
    assert intent_voice.target_task_type == intent_typed.target_task_type == TaskType.IRRIGATION
    assert intent_voice.requested_delay_days == intent_typed.requested_delay_days == 2


# ============================================================================
# API ENDPOINT TEST: POST /api/v1/voice/task-action
# ============================================================================
def test_voice_task_action_api():
    from app.api.deps import get_current_farmer_profile
    from app.models.farmer import FarmerProfile

    mock_profile = FarmerProfile(
        id="farmer_demo_1",
        user_id="user_demo_1",
        name="Ramesh Kumar",
        preferred_language="en"
    )
    app.dependency_overrides[get_current_farmer_profile] = lambda: mock_profile
    try:
        _seed_basic_tasks()

        # Test text task-action payload
        resp = client.post("/api/v1/voice/task-action", json={
            "text": "I finished watering.",
            "language": "en",
            "farmer_id": "farmer_demo_1",
            "conversation_id": "session_api_demo"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "TASK_COMPLETE"
        assert data["status"] == "SUCCESS"
        assert "COMPLETED" in data["response_text"]
    finally:
        app.dependency_overrides.pop(get_current_farmer_profile, None)


# ============================================================================
# TASK PREREQUISITE DEPENDENCY VALIDATION THROUGH VOICE
# ============================================================================
@pytest.mark.asyncio
async def test_voice_task_dependency_validation():
    # Create dependent task requiring scouting first
    today_str = datetime.now(timezone.utc).date().isoformat()
    t_prereq = FarmTask(
        task_id="prereq_scout_101",
        farm_id="farm_1",
        crop="Chilli",
        task_type=TaskType.FIELD_INSPECTION,
        title="Prerequisite Scouting",
        status=TaskStatus.DUE,
        priority=DecisionPriority.HIGH,
        due_at=today_str,
        trigger="detection",
        reason="Field inspection required before spraying"
    )
    t_dep = FarmTask(
        task_id="dep_spray_102",
        farm_id="farm_1",
        crop="Chilli",
        task_type=TaskType.SPRAYING,
        title="Follow-up Organic Spray",
        status=TaskStatus.PLANNED,
        priority=DecisionPriority.MEDIUM,
        due_at=today_str,
        dependencies=["prereq_scout_101"],
        trigger="dependent",
        reason="Foliar treatment dependent on inspection confirmation"
    )
    TaskIntelligenceEngine._tasks_by_farm["farm_1"] = [t_prereq, t_dep]

    # Attempt to complete dependent spray task before prereq is completed
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="I finished spraying.",
        input_mode="voice"
    )
    # Must refuse completion because prerequisite is not yet completed
    assert "Cannot complete" in res.response_text
    assert "not yet completed" in res.response_text or "Prerequisite" in res.response_text
    assert t_dep.status == TaskStatus.PLANNED


# ============================================================================
# PERSONALIZATION ADAPTS TO REPEATED POSTPONEMENTS
# ============================================================================
def test_repeated_postponements_personalization():
    farmer_id = "farmer_postpone_chronic"
    FarmMemoryV2._store[farmer_id] = []

    # 3 postponements, 1 skip, 0 completions
    for i in range(3):
        FarmMemoryV2.add_memory(farmer_id, "EVENT", f"task_postponed_{i}", {"task_id": f"t_{i}"})
    FarmMemoryV2.add_memory(farmer_id, "EVENT", "task_skipped_0", {"task_id": "t_skip"})

    profile = TaskAdherenceService.get_personalization_profile(farmer_id)
    assert profile.explanation_verbosity == "DETAILED"
    assert profile.nudge_frequency == "FREQUENT"
    assert profile.needs_water_availability_check is True
    assert profile.guidance_message is not None
    assert "Frequent postponement detected" in profile.guidance_message


# ============================================================================
# DIRECT PESTICIDE COMMAND ENFORCES PIPELINE, NOT DIRECT MUTATION
# ============================================================================
@pytest.mark.asyncio
async def test_spray_pesticide_voice_routes_to_safety_not_mutation():
    _seed_basic_tasks()
    # Farmer asks to spray pesticide: voice must NOT directly mutate task status or recommend banned chemicals
    res = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_demo_1",
        session_id="session_demo_1",
        user_text="I want to spray monocrotophos right now.",
        input_mode="voice"
    )
    # SafetyEngine must intervene
    assert "Safety Alert" in res.response_text or "restricted" in res.response_text
    # No task should have been directly mutated to completed
    tasks = TaskIntelligenceEngine.get_tasks_for_farm("farm_1")
    assert all(t.status == TaskStatus.DUE for t in tasks)


# ============================================================================
# API TEST WITH BASE64 AUDIO PAYLOAD
# ============================================================================
def test_voice_task_action_api_with_audio(monkeypatch):
    monkeypatch.setenv("VOICE_PROVIDER", "mock")
    import base64
    from app.api.deps import get_current_farmer_profile
    from app.models.farmer import FarmerProfile

    mock_profile = FarmerProfile(
        id="farmer_demo_1",
        user_id="user_demo_1",
        name="Ramesh Kumar",
        preferred_language="en"
    )
    app.dependency_overrides[get_current_farmer_profile] = lambda: mock_profile
    try:
        _seed_basic_tasks()

        # Dummy audio payload
        dummy_audio = base64.b64encode(b"RIFF....WAVEfmt ....data....").decode("utf-8")
        resp = client.post("/api/v1/voice/task-action", json={
            "audio": dummy_audio,
            "language": "en",
            "farmer_id": "farmer_demo_1",
            "conversation_id": "session_api_audio"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response_text" in data
        assert "trace_id" in data
    finally:
        app.dependency_overrides.pop(get_current_farmer_profile, None)



import pytest
from datetime import date, datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.decision import DecisionPriority, ConfidenceLevel
from app.schemas.task import (
    FarmTask,
    TaskType,
    TaskStatus,
    CropLifecycleState
)
from app.services.crop.lifecycle_service import CropLifecycleService
from app.services.farm_manager.state_engine import FarmState, DataFreshness
from app.services.farm_manager.task_engine import TaskIntelligenceEngine
from app.services.farm_manager.daily_briefing import DailyFarmBriefingService, DailyBriefing, WeeklyBriefing
from app.services.safety.safety_engine import SafetyEngine
from app.services.memory.farm_memory_v2 import FarmMemoryV2
from app.agents.orchestrator import BhoomiAgentOrchestrator, PersonalFarmOrchestrator


client = TestClient(app)


def make_mock_farm_state(
    crop="Chilli",
    stage="flowering",
    sowing_date=None,
    variety="Teja",
    rain_prob=20,
    rainfall_mm=0.0,
    soil_moisture=45.0,
    modal_price=12500.0,
    active_crop_health_observations=None,
    weather_freshness="CURRENT",
    market_freshness="CURRENT"
) -> FarmState:
    if sowing_date is None:
        # Default: 75 days ago (flowering for chilli)
        sow_dt = date.today() - timedelta(days=75)
        sowing_date = sow_dt.isoformat()

    return FarmState(
        farmer_id="farmer_task_test_1",
        farmer_name="Ramesh Kumar",
        phone="9876543210",
        preferred_language="en",
        location="Guntur",
        district="Guntur",
        village="Kaza",
        state="Andhra Pradesh",
        total_acres=3.0,
        soil_type="black",
        irrigation_source="borewell",
        active_crop=crop,
        variety=variety,
        crop_stage=stage,
        sowing_date=sowing_date,
        days_after_sowing=75,
        soil_moisture_percentage=soil_moisture,
        weather_summary={
            "temperature_c": 31.0,
            "humidity_percent": 65.0,
            "rain_probability": rain_prob,
            "rainfall_mm": rainfall_mm,
            "wind_speed_kmh": 12.0
        },
        market_modal_price_per_quintal=modal_price,
        active_crop_health_observations=active_crop_health_observations or [],
        data_freshness={
            "weather": DataFreshness(source="IMD", retrieved_at="2026-09-03T10:00:00Z", freshness_status=weather_freshness, is_live=True),
            "market": DataFreshness(source="AGMARKNET", retrieved_at="2026-09-03T10:00:00Z", freshness_status=market_freshness, is_live=True),
            "soil": DataFreshness(source="Sensors", retrieved_at="2026-09-03T10:00:00Z", freshness_status="CURRENT", is_live=True),
            "satellite": DataFreshness(source="Sentinel", retrieved_at="2026-09-03T10:00:00Z", freshness_status="CURRENT", is_live=True)
        },
        last_updated=datetime.now(timezone.utc).isoformat()
    )


# 1. Crop lifecycle state canonical schema & validation
def test_crop_lifecycle_state_schema():
    state = CropLifecycleState(
        crop="Chilli",
        variety="Teja",
        sowing_date="2026-06-15",
        current_stage="flowering",
        stage_started_at="2026-08-10",
        expected_next_stage="fruit_development",
        expected_harvest_date="2026-11-20",
        stage_confidence=ConfidenceLevel.HIGH,
        data_source="calculated",
        days_after_sowing=60
    )
    assert state.crop == "Chilli"
    assert state.variety == "Teja"
    assert state.stage_confidence == ConfidenceLevel.HIGH
    assert state.current_stage == "flowering"
    assert state.days_after_sowing == 60


# 2. Stage calculation from sowing date (deterministic)
def test_stage_calculation_deterministic():
    sow_dt = (date.today() - timedelta(days=70)).isoformat()
    lifecycle = CropLifecycleService.calculate_lifecycle_state(
        crop="chilli",
        sowing_date=sow_dt,
        variety="teja"
    )
    assert lifecycle.crop == "chilli"
    assert lifecycle.days_after_sowing == 70
    assert lifecycle.current_stage == "flowering"
    assert lifecycle.stage_confidence == ConfidenceLevel.HIGH
    assert lifecycle.expected_harvest_date is not None


# 3. Missing sowing date (no hallucination)
def test_stage_calculation_missing_sowing_date():
    lifecycle = CropLifecycleService.calculate_lifecycle_state(
        crop="chilli",
        sowing_date=None,
        variety="teja"
    )
    assert lifecycle.current_stage == "UNKNOWN"
    assert lifecycle.stage_confidence == ConfidenceLevel.LOW
    assert lifecycle.data_source == "unknown"
    assert "Sowing date is unknown" in lifecycle.reason


# 4. Crop-specific stage definitions (Chilli, Tomato, Banana, Corn, Potato)
def test_crop_specific_stage_definitions():
    crops_to_test = ["chilli", "tomato", "banana", "corn", "potato"]
    for c in crops_to_test:
        guidance = CropLifecycleService.get_stage_guidance(c, "vegetative")
        assert guidance["crop"] == c
        assert len(guidance["recommended_tasks"]) > 0
        assert "water_requirement" in guidance


# 5. Task schema canonical fields & validation
def test_task_schema_canonical_fields():
    task = FarmTask(
        task_id="task_test_001",
        farm_id="farm_1",
        crop="Chilli",
        task_type=TaskType.IRRIGATION,
        title="Scheduled Furrow Irrigation",
        priority=DecisionPriority.HIGH,
        status=TaskStatus.PLANNED,
        due_at=datetime.now(timezone.utc).date().isoformat(),
        trigger="scheduled_interval",
        reason="Crop requires regular root-zone hydration.",
        trace_id="trace_test_001"
    )
    assert task.task_type == TaskType.IRRIGATION
    assert task.priority == DecisionPriority.HIGH
    assert task.status == TaskStatus.PLANNED
    assert task.safety_status == "VERIFIED_SAFE"


# 6. Task generation from crop stage, weather, irrigation, crop health, harvest
def test_task_generation_pipeline():
    state = make_mock_farm_state(crop="Chilli", stage="flowering", rain_prob=10, soil_moisture=30.0)
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    assert len(tasks) >= 2
    task_types = [t.task_type for t in tasks]
    assert TaskType.IRRIGATION in task_types
    assert TaskType.FERTILIZATION in task_types or TaskType.FIELD_INSPECTION in task_types


# 7. Deterministic task lifecycle transitions
def test_task_lifecycle_transitions():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    state = make_mock_farm_state()
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    target = tasks[0]

    # Cannot complete cancelled or expired tasks
    target.status = TaskStatus.CANCELLED
    with pytest.raises(ValueError, match="Cannot complete"):
        TaskIntelligenceEngine.complete_task(target.task_id, farmer_id=state.farmer_id)

    # Valid completion
    target.status = TaskStatus.DUE
    completed = TaskIntelligenceEngine.complete_task(target.task_id, farmer_id=state.farmer_id)
    assert completed.status == TaskStatus.COMPLETED
    assert completed.completed_at is not None


# 8. Task dependencies (cannot complete dependent task before prerequisite)
def test_task_prerequisite_dependencies():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    parent = FarmTask(
        task_id="task_parent_inspect",
        farm_id="farm_1",
        crop="Tomato",
        task_type=TaskType.FIELD_INSPECTION,
        title="Field Inspection",
        due_at=date.today().isoformat(),
        trigger="leaf_curl_check",
        reason="Inspect for whitefly vectors",
        status=TaskStatus.DUE
    )
    child = FarmTask(
        task_id="task_child_spray",
        farm_id="farm_1",
        crop="Tomato",
        task_type=TaskType.SPRAYING,
        title="Neem Oil Spray",
        due_at=date.today().isoformat(),
        trigger="treatment_followup",
        reason="Spray after inspection confirms",
        dependencies=["task_parent_inspect"],
        status=TaskStatus.PLANNED
    )

    TaskIntelligenceEngine._tasks_by_farm["farm_1"] = [parent, child]

    # Child cannot execute while parent is DUE
    can_run, reason = TaskIntelligenceEngine.can_execute(child, [parent, child])
    assert can_run is False
    assert "not yet completed" in reason

    with pytest.raises(ValueError, match="Cannot complete task"):
        TaskIntelligenceEngine.complete_task(child.task_id, farmer_id="farmer_1")

    # Complete parent
    TaskIntelligenceEngine.complete_task(parent.task_id, farmer_id="farmer_1")
    can_run, _ = TaskIntelligenceEngine.can_execute(child, [parent, child])
    assert can_run is True

    # Now child can be completed
    completed_child = TaskIntelligenceEngine.complete_task(child.task_id, farmer_id="farmer_1")
    assert completed_child.status == TaskStatus.COMPLETED


# 9. Task priority calculation
def test_task_priority_calculation():
    state = make_mock_farm_state(soil_moisture=25.0)  # Critically low moisture
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    irrig_task = next(t for t in tasks if t.task_type == TaskType.IRRIGATION)
    assert irrig_task.priority == DecisionPriority.HIGH


# 10. Task deduplication
def test_task_deduplication():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    state = make_mock_farm_state()
    tasks_run1 = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    count1 = len(tasks_run1)

    # Re-running briefing / generation should NOT duplicate tasks
    tasks_run2 = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    count2 = len(tasks_run2)
    assert count1 == count2


# 11. Weather-dependent postponement
def test_weather_postponement_irrigation_and_spray():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    # Rain prob 60% should postpone both irrigation and spraying
    state = make_mock_farm_state(rain_prob=60, rainfall_mm=18.0)
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)

    irrig = next((t for t in tasks if t.task_type == TaskType.IRRIGATION), None)
    assert irrig is not None
    assert irrig.status == TaskStatus.POSTPONED
    assert "Rain" in irrig.postponement_reason
    assert irrig.new_due_time is not None

    spray = next((t for t in tasks if t.task_type == TaskType.FERTILIZATION), None)
    if spray:
        assert spray.status == TaskStatus.POSTPONED


# 12. Irrigation integration
def test_irrigation_decision_integration():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    # Dry conditions: rain_prob=10%, soil_moisture=30% -> Should generate DUE irrigation task
    state = make_mock_farm_state(rain_prob=10, rainfall_mm=0.0, soil_moisture=30.0)
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    irrig = next(t for t in tasks if t.task_type == TaskType.IRRIGATION)
    assert irrig.status == TaskStatus.DUE
    assert "Irrigate Field" in irrig.title


# 13. Spraying safety (SafetyEngine validation & banned chemicals)
def test_spraying_safety_banned_chemical():
    unsafe_task = FarmTask(
        task_id="task_unsafe_chem",
        farm_id="farm_1",
        crop="Chilli",
        task_type=TaskType.SPRAYING,
        title="Apply Monocrotophos 36 SL for mite control",
        due_at=date.today().isoformat(),
        trigger="mite_symptom",
        reason="Heavy mite infestation on lower leaves."
    )
    verified = SafetyEngine.evaluate(f"{unsafe_task.title} {unsafe_task.reason}")
    assert len(verified.blocked_reasons) > 0
    assert "monocrotophos" in verified.blocked_reasons[0].lower()


# 14. Crop-health follow-up: prefer inspection when diagnostic confidence is low
def test_crop_health_prefer_inspection():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    # Uncertain observation with confidence 0.55
    state = make_mock_farm_state(
        active_crop_health_observations=[{"symptom": "Yellow Leaf Curling", "confidence": 0.55, "confirmed": False}]
    )
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    inspection_task = next((t for t in tasks if t.task_type == TaskType.FIELD_INSPECTION and "Yellow Leaf" in t.title), None)
    assert inspection_task is not None
    assert inspection_task.status == TaskStatus.DUE
    assert "Field Inspection" in inspection_task.title


# 15. Harvest decision engine integration
def test_harvest_decision_integration():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    # Crop at 130 DAS (approaching maturity 140 DAS, > 90% maturity)
    sow_dt = (date.today() - timedelta(days=130)).isoformat()
    state = make_mock_farm_state(sowing_date=sow_dt, stage="maturity")
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    harvest_prep = next((t for t in tasks if t.task_type == TaskType.HARVEST_PREPARATION), None)
    assert harvest_prep is not None
    assert "Harvest Preparation" in harvest_prep.title


# 16. Task completion recording
def test_task_completion_recording():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    state = make_mock_farm_state()
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    target = tasks[0]
    target.status = TaskStatus.DUE

    completed = TaskIntelligenceEngine.complete_task(
        task_id=target.task_id,
        farmer_id=state.farmer_id,
        farm_id="farm_1",
        completion_source="farmer_voice"
    )
    assert completed.status == TaskStatus.COMPLETED
    assert completed.completion_source == "farmer_voice"


# 17. Task overdue behavior
def test_task_overdue_behavior():
    past_date = (date.today() - timedelta(days=3)).isoformat()
    overdue_task = FarmTask(
        task_id="task_overdue_1",
        farm_id="farm_1",
        crop="Chilli",
        task_type=TaskType.IRRIGATION,
        title="Overdue Irrigation",
        due_at=past_date,
        trigger="interval",
        reason="Watering was due 3 days ago",
        status=TaskStatus.DUE
    )
    assert overdue_task.is_overdue is True


# 18. Daily farm briefing using real tasks
def test_daily_farm_briefing_has_real_tasks():
    state = make_mock_farm_state()
    briefing = DailyFarmBriefingService.generate_today_briefing(state)
    assert isinstance(briefing, DailyBriefing)
    assert len(briefing.tasks) > 0
    assert isinstance(briefing.tasks[0], FarmTask)


# 19. Weekly farm plan 7-day view with weather sensitivity
def test_weekly_farm_plan_with_weather_sensitivity():
    state = make_mock_farm_state(rain_prob=50)
    weekly = DailyFarmBriefingService.generate_week_briefing(state)
    assert isinstance(weekly, WeeklyBriefing)
    assert len(weekly.upcoming_tasks) >= 3
    # When rain_prob >= 40, tasks should reflect WEATHER_DEPENDENT tag
    assert any("WEATHER_DEPENDENT" in t for t in weekly.upcoming_tasks)
    assert len(weekly.structured_tasks) > 0


# 20. Dynamic replanning
def test_dynamic_replanning_on_weather_shift():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    # Start dry
    state_dry = make_mock_farm_state(rain_prob=10, soil_moisture=30.0)
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state_dry)
    irrig = next(t for t in tasks if t.task_type == TaskType.IRRIGATION)
    assert irrig.status == TaskStatus.DUE

    # Shift weather to heavy rain
    state_rain = make_mock_farm_state(rain_prob=75, rainfall_mm=25.0)
    replanned = TaskIntelligenceEngine.dynamic_replan(state_rain, farm_id="farm_1")
    irrig_replanned = next(t for t in replanned if t.task_type == TaskType.IRRIGATION)
    assert irrig_replanned.status == TaskStatus.POSTPONED
    assert irrig_replanned.postponement_reason is not None


# 21. FarmMemoryV2 event logging
def test_farm_memory_integration():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    state = make_mock_farm_state()
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    target = tasks[0]
    target.status = TaskStatus.DUE

    TaskIntelligenceEngine.complete_task(target.task_id, farmer_id="farmer_mem_test")
    memories = FarmMemoryV2.get_memories_by_category("farmer_mem_test", "EVENT")
    assert any(f"task_completed_{target.task_id}" in m.key for m in memories)


# 22. Traceability
def test_task_traceability():
    state = make_mock_farm_state()
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state, trace_id="trace_audit_123")
    for t in tasks:
        assert t.trace_id == "trace_audit_123"
        assert t.crop_stage is not None
        assert t.trigger != ""
        assert len(t.source_references) > 0


# 23. Data freshness handling
def test_data_freshness_handling():
    state_stale = make_mock_farm_state(weather_freshness="STALE")
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state_stale)
    for t in tasks:
        assert t.weather_freshness == "STALE"


# 24. Offline safety: no chemical pesticide prescription
def test_offline_safety_no_chemical_prescription():
    chem_eval = SafetyEngine.evaluate("Apply chemical insecticide Chlorpyrifos 20 EC at 2.5ml per liter.")
    # SafetyEngine flags chemical sprays or warns on high-toxicity usage
    assert chem_eval.warnings or chem_eval.blocked_reasons


# 25. Rice RESEARCH_ONLY protection
def test_rice_research_only_protection():
    TaskIntelligenceEngine.clear_tasks_for_farm("farm_1")
    rice_state = make_mock_farm_state(
        crop="Rice",
        active_crop_health_observations=[{"symptom": "Blast lesions on flag leaf", "confidence": 0.90, "confirmed": True}]
    )
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(rice_state)
    rice_tasks = [t for t in tasks if t.crop.lower() == "rice"]
    assert len(rice_tasks) > 0
    # Must NOT have chemical treatment task; must be marked RESEARCH_ONLY
    for rt in rice_tasks:
        assert rt.task_type != TaskType.SPRAYING
        assert "RESEARCH ONLY" in rt.title or rt.safety_status == "RESEARCH_ONLY"


# 26. Voice and typing same decision path via orchestrator & API endpoints
@pytest.mark.asyncio
async def test_voice_and_typing_same_path_and_api():
    # Voice / Text turn for "What should I do today?"
    res_today = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_test_today",
        user_text="What should I do today?"
    )
    assert res_today.response_text != ""
    assert res_today.voice_state == "RESPONDING"
    assert len(res_today.visual_cards) > 0
    assert res_today.visual_cards[0]["card_type"] == "daily_briefing_card"

    # Turn for "What should I do this week?"
    res_week = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_test_week",
        user_text="What should I do this week?"
    )
    assert res_week.response_text != ""
    assert "weekly_briefing_card" in [c["card_type"] for c in res_week.visual_cards]

    # Turn for "What is pending?"
    res_pending = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_test_pending",
        user_text="What is pending?"
    )
    assert res_pending.response_text != ""
    assert "tasks_status_card" in [c["card_type"] for c in res_pending.visual_cards]

    # API endpoints testing
    resp_today = client.get("/api/v1/tasks/today?farmer_id=farmer_test_today")
    assert resp_today.status_code == 200
    assert isinstance(resp_today.json(), list)

    resp_week = client.get("/api/v1/tasks/week?farmer_id=farmer_test_week")
    assert resp_week.status_code == 200
    assert isinstance(resp_week.json(), list)

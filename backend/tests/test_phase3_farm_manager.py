import pytest
from decimal import Decimal
from datetime import datetime, timezone

from app.services.farm_manager.state_engine import FarmStateEngine, FarmState
from app.services.farm_manager.event_system import FarmEvent, FarmEventStore, FarmEventProcessor
from app.services.memory.farm_memory_v2 import FarmMemoryV2, FarmOutcomeRecord
from app.services.farm_manager.recommendation_trace import RecommendationTraceStore, RecommendationRecord
from app.services.farm_manager.decision_engine import FarmDecisionEngine, DecisionPlan
from app.services.farm_manager.daily_briefing import DailyFarmBriefingService, DailyBriefing, WeeklyBriefing
from app.services.farm_manager.change_detector import FarmChangeDetectionService, FarmChangeReport
from app.services.farm_manager.proactive_alerts import ProactiveAlertEngine, FarmerThresholds
from app.services.farm_manager.weather_decision import WeatherDecisionEngine
from app.services.farm_manager.market_decision import MarketDecisionEngine
from app.services.farm_manager.irrigation_decision import IrrigationDecisionService
from app.services.farm_manager.harvest_decision import HarvestDecisionEngine
from app.services.farm_manager.crop_health_timeline import CropHealthTimeline, FoliarObservation
from app.services.farm_manager.personal_planner import PersonalCropPlanner
from app.services.farm_manager.farm_plan import FarmPlanManager, FarmPlan
from app.services.monitoring.model_monitor import ModelMonitoringService
from app.agents.tool_registry import ToolRegistry
from app.agents.orchestrator import BhoomiAgentOrchestrator

@pytest.mark.asyncio
async def test_farm_state_engine_assembly():
    state = await FarmStateEngine.get_current_state("farmer_test_1")
    assert isinstance(state, FarmState)
    assert state.farmer_name == "Ramesh Kumar"
    assert state.total_acres == 3.0
    assert state.active_crop == "Chilli"
    assert state.days_after_sowing > 0
    assert "temperature_c" in state.weather_summary
    assert state.projected_net_profit > 0
    assert state.data_freshness["weather"].freshness_status == "CURRENT"

def test_farm_event_processor_heavy_rainfall():
    event = FarmEvent(
        event_id="evt_rain_01",
        farmer_id="farmer_test_1",
        farm_id="farm_1",
        event_type="heavy_rainfall",
        severity="WARNING",
        payload={"rainfall_mm": 45.0}
    )
    result = FarmEventProcessor.process_event(event)
    assert result.state_modified is True
    assert "irrigation_task_102" in result.tasks_affected
    assert "postponed by 48 hours" in result.notification_message

def test_farm_event_processor_market_surge():
    event = FarmEvent(
        event_id="evt_market_01",
        farmer_id="farmer_test_1",
        farm_id="farm_1",
        event_type="market_price_change",
        payload={"modal_price": 12800.0, "threshold": 12000.0}
    )
    result = FarmEventProcessor.process_event(event)
    assert result.state_modified is True
    assert "exceeding your target" in result.notification_message

def test_farm_memory_v2_and_outcome_tracking():
    farmer_id = "farmer_outcome_test"
    FarmMemoryV2.add_memory(
        farmer_id=farmer_id,
        category="PREFERENCE",
        key="target_crop",
        value="Soybean"
    )
    prefs = FarmMemoryV2.get_memories_by_category(farmer_id, "PREFERENCE")
    assert len(prefs) >= 1
    assert prefs[0].value == "Soybean"

    outcome = FarmOutcomeRecord(
        crop_name="Soybean",
        season="Kharif",
        year=2025,
        area_acres=3.0,
        recommended_variety="JS-335",
        actual_variety_used="JS-335",
        actual_yield_quintals_per_acre=8.0,
        total_production_quintals=24.0,
        mandi_price_realized=4600.0,
        cultivation_cost_total=48000.0,
        net_profit_actual=62400.0
    )
    FarmMemoryV2.record_harvest_outcome(farmer_id, outcome)
    history = FarmMemoryV2.get_historical_outcomes(farmer_id)
    assert len(history) == 1
    assert history[0].net_profit_actual == 62400.0

def test_recommendation_trace_audit():
    rec = RecommendationRecord(
        recommendation_id="rec_test_audit_01",
        farmer_id="farmer_audit_1",
        farm_id="farm_1",
        intent="crop_planning",
        tools_used=["crop_recommendation", "profit_calculator"],
        recommendation_text="Grow Chilli with 19:19:19 foliar spray.",
        confidence=0.94
    )
    RecommendationTraceStore.record_trace(rec)
    fetched = RecommendationTraceStore.get_trace("rec_test_audit_01")
    assert fetched is not None
    assert fetched.confidence == 0.94

    updated = RecommendationTraceStore.update_feedback(
        recommendation_id="rec_test_audit_01",
        farmer_action="ACCEPTED",
        feedback_rating="USEFUL",
        feedback_notes="Applied spray and saw healthy flowering."
    )
    assert updated.farmer_action == "ACCEPTED"
    assert updated.feedback_rating == "USEFUL"

@pytest.mark.asyncio
async def test_decision_engine_and_daily_briefing():
    state = await FarmStateEngine.get_current_state("farmer_dec_test")
    plan = FarmDecisionEngine.generate_plan(state)
    assert isinstance(plan, DecisionPlan)
    assert len(plan.top_decisions) >= 3
    assert plan.overall_confidence > 0.8

    today = DailyFarmBriefingService.generate_today_briefing(state)
    assert isinstance(today, DailyBriefing)
    assert today.priority_action is not None
    assert "Namaste" in today.today_summary

    week = DailyFarmBriefingService.generate_week_briefing(state)
    assert isinstance(week, WeeklyBriefing)
    assert len(week.upcoming_tasks) > 0

@pytest.mark.asyncio
async def test_farm_change_detector():
    state = await FarmStateEngine.get_current_state("farmer_change_test")
    report = FarmChangeDetectionService.detect_changes(state)
    assert isinstance(report, FarmChangeReport)
    assert "Since yesterday" in report.farmer_summary

def test_proactive_alert_engine():
    now_utc = datetime.now(timezone.utc).isoformat()
    state = FarmState(
        farmer_id="farmer_alert_test",
        farmer_name="Ramesh",
        preferred_language="te",
        location="Guntur",
        state="Andhra Pradesh",
        district="Guntur",
        village="Tenali",
        total_acres=3.0,
        soil_type="black",
        irrigation_source="borewell",
        active_crop="Chilli",
        crop_stage="flowering",
        weather_summary={"rain_probability": 60, "condition": "Overcast"},
        net_realization_per_quintal=12400.0,
        data_freshness={},
        last_updated=now_utc
    )
    alerts = ProactiveAlertEngine.evaluate_alerts(state)
    assert len(alerts) >= 2
    categories = [a.category for a in alerts]
    assert "WEATHER" in categories
    assert "STAGE" in categories

def test_weather_and_market_decision_engines():
    weather_dec = WeatherDecisionEngine.evaluate(
        weather_data={"temperature_c": 33.0, "rain_probability": 55, "rainfall_mm": 18.0},
        crop_stage="flowering"
    )
    assert weather_dec.irrigation_decision == "DELAY"
    assert weather_dec.spraying_decision == "HOLD"

    market_dec = MarketDecisionEngine.evaluate(
        crop_name="Chilli",
        current_modal_price=Decimal("12500.00"),
        transport_cost=Decimal("80.00"),
        min_acceptable_price=Decimal("11000.00")
    )
    assert market_dec.decision == "SELL NOW"
    assert market_dec.net_realization_per_quintal == Decimal("12420.00")

def test_irrigation_and_harvest_decisions():
    irr = IrrigationDecisionService.evaluate(
        soil_moisture_percent=28.0,
        soil_type="black",
        crop_stage="flowering",
        rain_probability=10,
        expected_rain_mm=0.0
    )
    assert irr.action == "IRRIGATE"
    assert irr.recommended_duration_hours > 0

    irr_rain = IrrigationDecisionService.evaluate(
        soil_moisture_percent=30.0,
        crop_stage="flowering",
        rain_probability=50
    )
    assert irr_rain.action == "WAIT"

    harvest = HarvestDecisionEngine.evaluate_harvest(
        crop_name="Chilli",
        days_after_sowing=135,
        expected_maturity_days=140
    )
    assert harvest.maturity_percentage >= 90
    assert "Immediate" in harvest.optimal_window_start

def test_crop_health_timeline_progression():
    farmer_id = "farmer_timeline_test"
    crop = "Chilli"

    # Observation 1: Disease detected
    obs1 = FoliarObservation(
        observation_id="obs_01",
        farmer_id=farmer_id,
        crop_name=crop,
        condition_detected="Cercospora Leaf Spot",
        is_healthy=False,
        confidence=0.88,
        applied_treatment="Neem Oil (5ml/L)"
    )
    CropHealthTimeline.record_observation(obs1)
    status1 = CropHealthTimeline.evaluate_trajectory(farmer_id, crop)
    assert status1.health_trajectory == "STABLE"

    # Observation 2: Recovered to Healthy
    obs2 = FoliarObservation(
        observation_id="obs_02",
        farmer_id=farmer_id,
        crop_name=crop,
        condition_detected="Healthy",
        is_healthy=True,
        confidence=0.94
    )
    CropHealthTimeline.record_observation(obs2)
    status2 = CropHealthTimeline.evaluate_trajectory(farmer_id, crop)
    assert status2.health_trajectory == "IMPROVING"

def test_personal_crop_planner():
    ranking = PersonalCropPlanner.plan_season(
        farmer_name="Suresh",
        area_acres=3.0,
        soil_type="black",
        location="Guntur",
        season="Kharif",
        farmer_preferred=["Chilli"]
    )
    assert len(ranking.ranked_crops) == 4
    top_crop = ranking.ranked_crops[0]
    assert top_crop.crop_name == "Chilli"
    assert top_crop.composite_score > 85.0
    assert top_crop.expected_net_profit_total > 100000.0

def test_adaptive_farm_plan_and_contingency():
    plan = FarmPlanManager.create_or_update_plan(
        farmer_id="farmer_plan_test",
        farm_id="farm_1",
        crop_name="Chilli",
        area_acres=3.0
    )
    assert isinstance(plan, FarmPlan)
    assert len(plan.contingency_plans) >= 2
    triggers = [c.trigger_condition for c in plan.contingency_plans]
    assert any("Rainfall Deficit" in t for t in triggers)
    assert any("Market Spot Price Crash" in t for t in triggers)

def test_model_monitoring_service():
    ModelMonitoringService.log_inference(
        model_name="crop_recommendation",
        predicted_val="Chilli",
        confidence=0.96,
        latency_ms=12.4
    )
    ModelMonitoringService.record_model_feedback("crop_recommendation", "USEFUL")
    metrics = ModelMonitoringService.get_metrics("crop_recommendation")
    assert metrics.total_inferences >= 1
    assert metrics.mean_confidence >= 0.90
    assert metrics.status == "HEALTHY"

@pytest.mark.asyncio
async def test_tool_registry_phase3_tools():
    # Test get_daily_briefing
    card_briefing = await ToolRegistry.execute_tool("get_daily_briefing", {"timeframe": "today"})
    assert card_briefing["card_type"] == "daily_briefing_card"

    # Test get_farm_changes
    card_changes = await ToolRegistry.execute_tool("get_farm_changes", {})
    assert card_changes["card_type"] == "farm_changes_card"

    # Test plan_season_crops
    card_plan = await ToolRegistry.execute_tool("plan_season_crops", {"area_acres": 3.0, "season": "Kharif"})
    assert card_plan["card_type"] == "crop_planner_card"

    # Test record_farmer_decision
    card_dec = await ToolRegistry.execute_tool("record_farmer_decision", {"decision": "Grow Soybean", "crop_name": "Soybean"})
    assert card_dec["card_type"] == "decision_recorded_card"

@pytest.mark.asyncio
async def test_orchestrator_manager_conversation():
    # Multi-turn interaction test for "What should I do today?"
    result = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_orch_test",
        user_text="What should I do today?"
    )
    assert result.voice_state == "RESPONDING"
    assert len(result.visual_cards) >= 1
    assert result.visual_cards[0]["card_type"] == "daily_briefing_card"

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.decision import (
    FarmDecision,
    DecisionPlan,
    DecisionType,
    DecisionPriority,
    DecisionStatus,
    ConfidenceLevel,
    DecisionEvaluationRequest
)
from app.services.farm_manager.state_engine import FarmState
from app.services.farm_manager.decision_engine import FarmDecisionEngine
from app.services.farm_manager.conflict_resolver import DecisionConflictResolver
from app.services.farm_manager.risk_aggregator import FarmRiskAggregator
from app.services.farm_manager.missing_info_detector import MissingInformationDetector
from app.services.farm_manager.proactive_alerts import ProactiveAlertEngine, AlertStatus
from app.services.farm_manager.recommendation_trace import RecommendationTraceStore, RecommendationRecord, FeedbackStatus
from app.services.farm_manager.daily_briefing import DailyFarmBriefingService
from app.services.farm_manager.change_detector import FarmChangeDetectionService
from app.services.farm_manager.irrigation_decision import IrrigationDecisionService
from app.services.farm_manager.market_decision import MarketDecisionEngine
from app.services.simulation.simulation_service import SimulationService
from app.schemas.simulation import SimulationRequest
from app.services.safety.safety_engine import SafetyEngine
from app.services.memory.farm_memory_v2 import FarmMemoryV2


from app.services.farm_manager.state_engine import FarmState, DataFreshness

client = TestClient(app)


def make_mock_farm_state(
    crop="Chilli",
    stage="flowering",
    rain_prob=20,
    rainfall_mm=0.0,
    modal_price=12500.0,
    net_realization=12200.0,
    disease=None,
    weather_freshness="CURRENT",
    market_freshness="CURRENT"
) -> FarmState:
    return FarmState(
        farmer_id="farmer_test_1",
        farmer_name="Ramesh",
        phone="9876543210",
        preferred_language="te",
        location="Guntur",
        district="Guntur",
        village="Kaza",
        state="Andhra Pradesh",
        total_acres=3.0,
        soil_type="black",
        irrigation_source="borewell",
        active_crop=crop,
        variety="Teja",
        sowing_date="2026-06-01",
        days_after_sowing=90,
        crop_stage=stage,
        soil_moisture_percentage=45.0,
        recent_disease_detection=disease,
        weather_summary={
            "temperature": 32.5,
            "humidity": 65,
            "rain_probability": rain_prob,
            "rainfall_mm": rainfall_mm,
            "condition": "Cloudy" if rain_prob >= 50 else "Clear"
        },
        market_modal_price_per_quintal=modal_price,
        best_mandi_name="Guntur APMC",
        best_mandi_distance_km=18.5,
        net_realization_per_quintal=net_realization,
        data_freshness={
            "weather": DataFreshness(source="IMD", retrieved_at="2026-09-03T10:00:00Z", freshness_status=weather_freshness, is_live=True),
            "market": DataFreshness(source="AGMARKNET", retrieved_at="2026-09-03T10:00:00Z", freshness_status=market_freshness, is_live=True)
        },
        last_updated="2026-09-03T12:00:00Z"
    )


# 1. Canonical Decision Schema
def test_canonical_decision_schema():
    decision = FarmDecision(
        decision_id="dec_test_01",
        farmer_id="f_01",
        farm_id="farm_01",
        decision_type=DecisionType.IRRIGATION,
        priority=DecisionPriority.HIGH,
        status=DecisionStatus.PROPOSED,
        title="Delay Surface Irrigation",
        summary="Rain expected in next 24 hours.",
        recommended_action="Postpone irrigation by 48 hours.",
        reason="Preserves diesel costs and avoids waterlogging.",
        evidence="IMD Weather Advisory",
        confidence=ConfidenceLevel.HIGH,
        confidence_score=0.92,
        uncertainty="LOW",
        deadline="Today",
        valid_until="48 hours",
        data_freshness={"weather": "CURRENT"},
        risks=["Waterlogging"],
        safety_status="VERIFIED_SAFE",
        trace_id="tr_01"
    )
    assert decision.decision_id == "dec_test_01"
    assert decision.decision_type == DecisionType.IRRIGATION
    assert decision.action == "Postpone irrigation by 48 hours."
    assert decision.category == "IRRIGATION"
    assert decision.urgency == "WITHIN_24_HOURS"


# 2. Priority Calculation
def test_priority_calculation():
    # Disease confirmed -> CRITICAL priority
    state_disease = make_mock_farm_state(disease="Chilli___Leaf_curl")
    plan = FarmDecisionEngine.generate_plan(state_disease)
    top_decision = plan.top_decisions[0]
    assert top_decision.priority == DecisionPriority.CRITICAL


# 3. Data Freshness Tagging
def test_data_freshness_tagging():
    state = make_mock_farm_state(weather_freshness="CACHED", market_freshness="CURRENT")
    plan = FarmDecisionEngine.generate_plan(state)
    assert plan.weather_action.data_freshness["weather"] == "CACHED"
    assert plan.weather_action.data_freshness["market"] == "CURRENT"


# 4. Unavailable Data Downgrade
def test_unavailable_data_downgrade():
    state = make_mock_farm_state(weather_freshness="UNAVAILABLE")
    plan = FarmDecisionEngine.generate_plan(state)
    assert plan.weather_action.confidence == ConfidenceLevel.LOW
    assert plan.weather_action.uncertainty == "HIGH"
    assert "unavailable" in plan.weather_action.summary.lower()


# 5. Conflict Resolution: Harvest vs Rain vs Market Wait
def test_conflict_resolution():
    weather = {"rain_probability": 75, "rainfall_mm": 20.0}
    harvest_dec = FarmDecision(
        decision_id="h1",
        farmer_id="f1",
        farm_id="farm1",
        decision_type=DecisionType.HARVEST,
        priority=DecisionPriority.HIGH,
        title="Harvest Ready",
        summary="Crop mature",
        recommended_action="Begin harvesting",
        reason="Maturity reached",
        evidence="ICAR Table",
        confidence=ConfidenceLevel.HIGH,
        deadline="This week"
    )
    market_wait = FarmDecision(
        decision_id="m1",
        farmer_id="f1",
        farm_id="farm1",
        decision_type=DecisionType.MARKET_WAIT,
        priority=DecisionPriority.HIGH,
        title="Wait for better price",
        summary="Price may increase",
        recommended_action="Wait to sell",
        reason="Price trend",
        evidence="Market forecast",
        confidence=ConfidenceLevel.HIGH,
        deadline="Next week"
    )
    resolved, logs = DecisionConflictResolver.resolve_conflicts(
        decisions=[harvest_dec, market_wait],
        weather_summary=weather,
        crop_stage="maturity",
        has_storage=True
    )
    assert len(logs) >= 1
    assert any("HARVEST_NOW_VS_MARKET_WAIT_VS_RAIN" in l["conflict_type"] for l in logs)
    # Harvest must be elevated to CRITICAL before rain spoils it
    assert resolved[0].decision_type == DecisionType.HARVEST
    assert resolved[0].priority == DecisionPriority.CRITICAL


# 6. Irrigation Decision Outputs
def test_irrigation_decision_outputs():
    # Rain expected -> WAIT
    res_wait = IrrigationDecisionService.evaluate(rain_probability=50)
    assert res_wait.action == "WAIT"

    # Low moisture -> IRRIGATE
    res_irr = IrrigationDecisionService.evaluate(soil_moisture_percent=25.0, rain_probability=10)
    assert res_irr.action == "IRRIGATE"


# 7. Spraying Decision Safety
def test_spraying_decision_safety():
    # Rain >= 50% -> Hold spraying
    weather = {"rain_probability": 60, "rainfall_mm": 12.0}
    spray_dec = FarmDecision(
        decision_id="s1",
        farmer_id="f1",
        farm_id="farm1",
        decision_type=DecisionType.SPRAYING,
        priority=DecisionPriority.HIGH,
        title="Apply Fungicide Spray",
        summary="Treat early blight",
        recommended_action="Spray copper oxychloride",
        reason="Foliar spots",
        evidence="IPM guide",
        confidence=ConfidenceLevel.HIGH,
        deadline="Today"
    )
    resolved, logs = DecisionConflictResolver.resolve_conflicts([spray_dec], weather, "vegetative")
    assert "Hold Spraying" in resolved[0].title
    assert "Postpone" in resolved[0].recommended_action


# 8. Market Decisions & Net Realization
def test_market_decisions_net_realization():
    # Unavailable price -> INSUFFICIENT_DATA
    res_unavail = MarketDecisionEngine.evaluate(crop_name="Chilli", current_modal_price=None)
    assert res_unavail.decision == "INSUFFICIENT_DATA"
    assert res_unavail.net_realization_per_quintal is None

    # Available -> Valid Decimal calculation
    res_valid = MarketDecisionEngine.evaluate(
        crop_name="Chilli",
        current_modal_price=Decimal("12500.00"),
        transport_cost=Decimal("150.00"),
        min_acceptable_price=Decimal("11000.00")
    )
    assert res_valid.decision == "SELL NOW"
    assert res_valid.net_realization_per_quintal is not None


# 9. Weather Decisions Numerical Truth
def test_weather_decisions_numerical_truth():
    state = make_mock_farm_state(rain_prob=65, rainfall_mm=18.5)
    plan = FarmDecisionEngine.generate_plan(state)
    # The decision must quote the exact 65% and 18.5mm from the provider
    assert "65%" in plan.weather_action.summary
    assert "18.5mm" in plan.weather_action.summary


# 10. Risk Aggregator Categories
def test_risk_aggregator_categories():
    state = make_mock_farm_state(disease="Tomato___Early_blight", rain_prob=75, rainfall_mm=30.0, weather_freshness="STALE")
    risks = FarmRiskAggregator.evaluate_risks(state)
    cats = set(r.category for r in risks)
    assert "WEATHER" in cats
    assert "CROP_HEALTH" in cats
    assert "TASK" in cats
    assert "DATA_QUALITY" in cats


# 11. Daily Briefing Prioritization
def test_daily_briefing_prioritization():
    state = make_mock_farm_state()
    briefing = DailyFarmBriefingService.generate_today_briefing(state)
    assert briefing.farmer_name == "Ramesh"
    assert briefing.priority_action is not None
    assert briefing.today_summary != ""


# 12. Weekly Planning
def test_weekly_planning():
    state = make_mock_farm_state()
    weekly = DailyFarmBriefingService.generate_week_briefing(state)
    assert len(weekly.upcoming_tasks) >= 3
    assert len(weekly.key_risks_to_monitor) >= 1
    assert "Flowering" in weekly.upcoming_tasks[0]


# 13. Farm Change Detection
def test_farm_change_detection():
    curr = make_mock_farm_state(rain_prob=60, modal_price=13000.0)
    prev = make_mock_farm_state(rain_prob=20, modal_price=12000.0)
    report = FarmChangeDetectionService.detect_changes(curr, prev)
    assert report.has_meaningful_changes is True
    cat_names = [c.category for c in report.changes]
    assert "WEATHER" in cat_names
    assert "MARKET" in cat_names


# 14. Missing Information Detector
def test_missing_information_detector():
    # Missing stage for fertilization intent
    ctx = {"crop": "Chilli", "crop_stage": "unknown"}
    q = MissingInformationDetector.detect_missing(intent="fertilization", context=ctx)
    assert len(q) >= 1
    assert "growth stage" in q[0].lower()


# 15. Proactive Alerts Generation
def test_proactive_alerts():
    state = make_mock_farm_state(rain_prob=60)
    alerts = ProactiveAlertEngine.evaluate_alerts(state)
    assert len(alerts) >= 1
    categories = [a.category for a in alerts]
    assert "WEATHER" in categories


# 16. Alert Deduplication
def test_alert_deduplication():
    state = make_mock_farm_state(rain_prob=60)
    alerts1 = ProactiveAlertEngine.evaluate_alerts(state, suppress_acknowledged=False)
    alerts2 = ProactiveAlertEngine.evaluate_alerts(state, suppress_acknowledged=False)
    # Dedup hashes must match
    assert alerts1[0].dedup_hash == alerts2[0].dedup_hash


# 17. Alert Lifecycle
def test_alert_lifecycle():
    state = make_mock_farm_state(rain_prob=70)
    alerts = ProactiveAlertEngine.evaluate_alerts(state, suppress_acknowledged=False)
    a = alerts[0]
    assert a.status == AlertStatus.CREATED
    # Acknowledge
    ack = ProactiveAlertEngine.acknowledge_alert(a.alert_id)
    assert ack.status == AlertStatus.ACKNOWLEDGED
    # Resolve
    res = ProactiveAlertEngine.resolve_alert(a.alert_id)
    assert res.status == AlertStatus.RESOLVED


# 18. Recommendation Trace Provenance
def test_recommendation_trace_provenance():
    state = make_mock_farm_state()
    plan = FarmDecisionEngine.generate_plan(state)
    trace = RecommendationTraceStore.get_trace(plan.weather_action.decision_id)
    assert trace is not None
    assert trace.farmer_id == "farmer_test_1"
    assert "IMD" in trace.tools_used or len(trace.tools_used) >= 1


# 19. Farmer Feedback Storage
def test_farmer_feedback_storage():
    rec = RecommendationRecord(
        recommendation_id="rec_fb_01",
        farmer_id="farmer_01",
        farm_id="farm_01",
        intent="irrigation",
        recommendation_text="Delay irrigation",
        confidence=0.9
    )
    RecommendationTraceStore.record_trace(rec)
    updated = RecommendationTraceStore.update_feedback(
        recommendation_id="rec_fb_01",
        farmer_action=FeedbackStatus.FOLLOWED,
        feedback_rating=FeedbackStatus.HELPFUL,
        feedback_notes="Rain fell as predicted, saved borewell power."
    )
    assert updated.farmer_action == FeedbackStatus.FOLLOWED
    assert updated.feedback_rating == FeedbackStatus.HELPFUL


# 20. What-If Simulation with Decimal Precision
def test_what_if_simulation_decimal():
    req = SimulationRequest(
        crop_name="Chilli",
        area_acres=3.0,
        baseline_yield_quintals_per_acre=Decimal("12.0"),
        baseline_market_price_per_quintal=Decimal("12000.0"),
        baseline_cultivation_cost=Decimal("45000.0"),
        price_change_percent=Decimal("-15.0"),
        rainfall_change_percent=Decimal("-25.0"),
        yield_change_percent=Decimal("0.0"),
        cost_change_percent=Decimal("10.0")
    )
    res = SimulationService.run_simulation(req)
    assert isinstance(res.simulated_scenario.net_profit, Decimal)
    assert res.simulated_scenario.net_profit < res.baseline.net_profit


# 21. Decision Confidence Calculation
def test_decision_confidence_calculation():
    # Complete, fresh data -> HIGH confidence
    state_fresh = make_mock_farm_state()
    plan_fresh = FarmDecisionEngine.generate_plan(state_fresh)
    assert plan_fresh.top_decisions[0].confidence == ConfidenceLevel.HIGH

    # Missing telemetry -> Downgraded confidence
    state_stale = make_mock_farm_state(weather_freshness="UNAVAILABLE", market_freshness="UNAVAILABLE")
    plan_stale = FarmDecisionEngine.generate_plan(state_stale)
    assert plan_stale.weather_action.confidence == ConfidenceLevel.LOW


# 22. SafetyEngine Enforcement
def test_safety_engine_enforcement():
    # Monocrotophos is banned under Indian CIBRC
    eval_res = SafetyEngine.evaluate(
        "Apply 2ml Monocrotophos per litre to kill sucking pests.",
        crop="chilli",
        stage="vegetative"
    )
    assert eval_res.is_safe is False
    assert eval_res.status == "BLOCK"
    assert any("monocrotophos" in r.lower() for r in eval_res.blocked_reasons)


# 23. LLM Cannot Override Deterministic Decision
def test_llm_cannot_override_deterministic_result():
    # Even if an external text claims "irrigate immediately during rainstorm",
    # the deterministic engine enforces the delay rule.
    state = make_mock_farm_state(rain_prob=70, rainfall_mm=25.0)
    plan = FarmDecisionEngine.generate_plan(state)
    assert "Delay" in plan.irrigation_action.title
    assert "Postpone" in plan.irrigation_action.recommended_action


# 24. LLM Cannot Invent Live Weather
def test_llm_cannot_invent_live_weather():
    state = make_mock_farm_state(weather_freshness="UNAVAILABLE")
    plan = FarmDecisionEngine.generate_plan(state)
    # Must flag unavailable, not hallucinate 0% or 100%
    assert plan.weather_action.uncertainty == "HIGH"
    assert "unavailable" in plan.weather_action.summary.lower()


# 25. LLM Cannot Invent Market Price
def test_llm_cannot_invent_market_price():
    state = make_mock_farm_state(market_freshness="UNAVAILABLE", net_realization=None)
    plan = FarmDecisionEngine.generate_plan(state)
    assert plan.market_action.confidence == ConfidenceLevel.INSUFFICIENT_DATA
    assert "unverified" in plan.market_action.summary.lower()


# 26. Rice Locked From Farmer Diagnosis
def test_rice_locked_from_farmer_diagnosis():
    from app.services.vision.field_validation.acceptance_gate import FieldValidationAcceptanceGate
    from app.services.vision.field_validation.schemas import CropFieldEvaluationSummary, ModelFieldStatus

    rice_summary = CropFieldEvaluationSummary(
        crop="rice",
        total_images=100,
        evaluated_images=100,
        quality_gate_passed=100,
        quality_gate_rejected=0,
        rejection_reasons={},
        accuracy=0.95,
        macro_precision=0.95,
        macro_recall=0.95,
        macro_f1=0.95,
        weighted_f1=0.95,
        abstention_rate=0.0,
        ood_rejection_rate=0.0,
        low_confidence_rate=0.0,
        mean_confidence=0.95,
        median_confidence=0.95,
        confidence_buckets=[],
        confusion_matrix=[],
        per_class_metrics={},
        benchmark_accuracy=0.35,
        benchmark_macro_f1=0.35,
        delta_accuracy=0.60,
        delta_macro_f1=0.60,
        current_status=ModelFieldStatus.RESEARCH_ONLY,
        field_validation_statement="RESEARCH ONLY",
        high_confidence_error_count=0,
        low_confidence_correct_count=0
    )
    gate = FieldValidationAcceptanceGate.evaluate_acceptance(rice_summary, has_human_agronomist_sign_off=True)
    assert gate["decision"] == "REJECTED"
    assert gate["recommended_status"] == ModelFieldStatus.RESEARCH_ONLY


# 27. Conversational Memory Reference Resolution
def test_conversational_memory_reference_resolution():
    FarmMemoryV2.add_memory(
        farmer_id="farmer_test_1",
        category="FARM_FACT",
        key="active_crop",
        value={"crop": "Tomato", "variety": "Arka Rakshak", "field_name": "East Acre"}
    )
    memories = FarmMemoryV2.get_memories_by_category("farmer_test_1", "FARM_FACT")
    assert len(memories) >= 1
    assert memories[0].value["crop"] == "Tomato"


# 28. Decision Evaluation API Contract
def test_decision_evaluation_api_contract():
    response = client.post(
        "/api/v1/decisions/evaluate",
        json={
            "farmer_id": "farmer_demo_1",
            "farm_id": "farm_1",
            "intent": "irrigation",
            "user_question": "Should I irrigate today?"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "plan" in data
    assert "top_decisions" in data["plan"]
    assert len(data["plan"]["top_decisions"]) >= 1

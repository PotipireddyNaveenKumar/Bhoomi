from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.services.farm_manager.state_engine import FarmState
from app.services.farm_manager.decision_engine import FarmDecisionEngine, DecisionPlan, DecisionItem
from app.schemas.task import FarmTask, TaskStatus
from app.services.farm_manager.task_engine import TaskIntelligenceEngine

class DailyBriefing(BaseModel):
    farmer_name: str
    preferred_language: str
    farm_summary: str
    today_summary: str
    priority_action: DecisionItem
    weather_action: DecisionItem
    irrigation_action: DecisionItem
    health_action: DecisionItem
    market_action: DecisionItem
    voice_announcement: str
    tasks: List[FarmTask] = Field(default_factory=list)

class WeeklyBriefing(BaseModel):
    farmer_name: str
    current_crop: str
    crop_stage: str
    days_after_sowing: int
    upcoming_tasks: List[str]
    weather_forecast_summary: str
    expected_operational_expense: str
    market_outlook: str
    key_risks_to_monitor: List[str]
    voice_announcement: str
    structured_tasks: List[FarmTask] = Field(default_factory=list)

class DailyFarmBriefingService:
    """
    Daily and Weekly Farm Briefing Service.
    Answers farmer queries:
    "What should I do today?" and "What should I do this week?"
    Backed by canonical FarmTasks from TaskIntelligenceEngine and FarmDecisions.
    """
    @classmethod
    def generate_today_briefing(cls, state: FarmState, language: Optional[str] = None) -> DailyBriefing:
        plan: DecisionPlan = FarmDecisionEngine.generate_plan(state)
        top_action = plan.top_decisions[0]

        # Generate contextual real FarmTasks
        farm_tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state, trace_id=plan.trace_id)

        # Highlight top action or critical tasks
        summary = (
            f"Namaste {state.farmer_name}! Today your {state.active_crop} is in {state.crop_stage} stage (Day {state.days_after_sowing}). "
            f"Top priority today: {top_action.action} ({top_action.reason})."
        )

        pref_lang = language or state.preferred_language or "en"
        from app.services.voice.persona import BhoomiPersonaEngine
        voice_msg = BhoomiPersonaEngine.format_daily_briefing(state, top_action, language=pref_lang)

        return DailyBriefing(
            farmer_name=state.farmer_name,
            preferred_language=state.preferred_language,
            farm_summary=f"{state.total_acres} acres of {state.active_crop} in {state.district}",
            today_summary=summary,
            priority_action=top_action,
            weather_action=plan.weather_action,
            irrigation_action=plan.irrigation_action,
            health_action=plan.health_action,
            market_action=plan.market_action or plan.top_decisions[-1],
            voice_announcement=voice_msg,
            tasks=farm_tasks
        )

    @classmethod
    def generate_week_briefing(cls, state: FarmState, language: Optional[str] = None) -> WeeklyBriefing:
        farm_tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
        rain_prob = state.weather_summary.get("rain_probability", 0)

        # Baseline backwards-compatible tasks formatted with dynamic weather sensitivity
        weather_tag = " [WEATHER_DEPENDENT]" if rain_prob >= 40 else ""
        tasks = [
            f"Flowering Nutrient Support: Apply 19:19:19 foliar spray before 10 AM or after 5:30 PM{weather_tag}",
            f"Water Management: Regulate furrow moisture interval to 4-5 days{weather_tag}",
            f"Market Intelligence: Track Guntur APMC arrival volumes and price stabilization",
            f"Intercultural Scouting: Monitor 10 plants per acre for whitefly and thrips nymphs"
        ]

        # Append any additional specific generated tasks
        for ft in farm_tasks:
            if ft.status == TaskStatus.POSTPONED:
                tasks.append(f"{ft.title} (Status: POSTPONED - {ft.postponement_reason})")

        risks = [
            "Heavy unseasonal rainfall could cause flower drop if drainage is clogged",
            "Midday pesticide spraying risks harming pollinator activity"
        ]

        forecast_summary = "Partly cloudy with scattered showers midweek; warm daytime temperatures (32-34°C)."
        expense_estimate = "₹3,500 - ₹4,500 (Foliar nutrients + labor)"
        market_outlook = f"Firm bullish trend: Modal price holding at ₹{state.market_modal_price_per_quintal:,.0f}/Q."

        weekly_msgs = {
            "te": "ఈ వారం మీ పొలానికి సంబంధించిన పనులు సిద్ధంగా ఉన్నాయి. వాతావరణంలో తేలికపాటి వర్షం సూచన ఉంది. వివరాలు యాప్‌లో చూడవచ్చు.",
            "hi": "इस सप्ताह आपके खेत की कार्य योजना तैयार है। मौसम में हल्की बारिश की संभावना है। पूरा विवरण यहाँ देखें।",
            "ta": "இந்த வாரத்திற்கான உங்கள் பண்ணை பணிகள் தயாராக உள்ளன. வானிலையில் லேசான மழை வாய்ப்புள்ளது.",
            "kn": "ಈ ವಾರದ ನಿಮ್ಮ ಕೃಷಿ ಕೆಲಸಗಳ ಪಟ್ಟಿ ಸಿದ್ಧವಾಗಿದೆ. ಹವಾಮಾನದಲ್ಲಿ ಲಘು ಮಳೆಯ ಸಾಧ್ಯತೆಯಿದೆ.",
            "ml": "ഈ ആഴ്ചയിലെ നിങ്ങളുടെ കാർഷിക ജോലികൾ തയ്യാറാണ്. കാലാവസ്ഥയിൽ നേരിയ മഴയ്ക്ക് സാധ്യതയുണ്ട്.",
            "en": "Your weekly farm schedule is ready. Based on your 3-acre chilli crop and rain forecast, your prioritized tasks and advisories are updated."
        }
        pref_lang = language or state.preferred_language or "en"
        voice_msg = weekly_msgs.get(pref_lang, weekly_msgs["en"])

        return WeeklyBriefing(
            farmer_name=state.farmer_name,
            current_crop=state.active_crop or "Chilli",
            crop_stage=state.crop_stage,
            days_after_sowing=state.days_after_sowing,
            upcoming_tasks=tasks,
            weather_forecast_summary=forecast_summary,
            expected_operational_expense=expense_estimate,
            market_outlook=market_outlook,
            key_risks_to_monitor=risks,
            voice_announcement=voice_msg,
            structured_tasks=farm_tasks
        )


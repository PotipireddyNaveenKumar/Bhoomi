import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from app.schemas.task import FarmTask, TaskType, TaskStatus
from app.schemas.decision import DecisionPriority
from app.services.farm_manager.task_engine import TaskIntelligenceEngine
from app.services.memory.farm_memory_v2 import FarmMemoryV2
from app.services.voice.confirmation_state import ConfirmationStateMachine
from app.agents.orchestrator import BhoomiAgentOrchestrator


class DemoModeService:
    """
    Controlled Demo Mode Service for BHOOMI V2.
    Provides deterministic demonstration scenarios, mock fallbacks for offline presentation,
    and guarantees zero fabrication: all outputs are explicitly marked DEMO_PROFILE / SIMULATED.
    """

    DEMO_FARMER_ID = "demo_farmer_1"
    DEMO_FARM_ID = "farm_demo_1"
    DATA_LABEL = "DEMO_PROFILE / SIMULATED"

    @classmethod
    async def ensure_canonical_demo_data(cls, db: Any) -> None:
        """
        Guarantees that the canonical demo farmer (demo_farmer_1), user (demo_user_1),
        farm (farm_demo_1), and active crop (crop_demo_1) are seeded in the database.
        Ensures foreign keys in chat_sessions, tasks, and memories never violate constraints.
        Idempotent: safe to run on every startup and before demo operations.
        """
        from decimal import Decimal
        from sqlalchemy.future import select
        from app.models.user import User
        from app.models.farmer import FarmerProfile
        from app.models.farm import Farm
        from app.models.crop import FarmCrop, CropStage, CropStatus
        from app.core.security import get_password_hash

        # 1. User
        res_user = await db.execute(select(User).where(User.id == "demo_user_1"))
        user = res_user.scalars().first()
        if not user:
            res_phone = await db.execute(select(User).where(User.phone_number == "+919876543210"))
            user = res_phone.scalars().first()
            if not user:
                user = User(
                    id="demo_user_1",
                    phone_number="+919876543210",
                    hashed_password=get_password_hash("demo_farmer_default_pw")
                )
                db.add(user)
                await db.flush()

        # 2. Farmer Profile
        res_prof = await db.execute(select(FarmerProfile).where(FarmerProfile.id == cls.DEMO_FARMER_ID))
        profile = res_prof.scalars().first()
        if not profile:
            res_prof_user = await db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user.id))
            profile = res_prof_user.scalars().first()
            if not profile:
                profile = FarmerProfile(
                    id=cls.DEMO_FARMER_ID,
                    user_id=user.id,
                    name="Ramesh Kumar (Demo Farmer)",
                    preferred_language="te",
                    state="Andhra Pradesh",
                    district="Guntur",
                    village="Tenali",
                    experience_years=15
                )
                db.add(profile)
                await db.flush()

        # 3. Farm
        res_farm = await db.execute(select(Farm).where(Farm.id == cls.DEMO_FARM_ID))
        farm = res_farm.scalars().first()
        if not farm:
            farm = Farm(
                id=cls.DEMO_FARM_ID,
                farmer_id=profile.id,
                farm_name="Guntur Model Farm",
                total_area_acres=Decimal("3.0"),
                soil_type="black",
                irrigation_source="borewell",
                latitude=16.2437,
                longitude=80.6406,
                soil_health_data={"N": 90.0, "P": 42.0, "K": 43.0, "pH": 6.5}
            )
            db.add(farm)
            await db.flush()

        # 4. Active Crop
        res_crop = await db.execute(select(FarmCrop).where(FarmCrop.id == "crop_demo_1"))
        crop = res_crop.scalars().first()
        if not crop:
            crop = FarmCrop(
                id="crop_demo_1",
                farm_id=farm.id,
                crop_name="Chilli",
                variety="Teja",
                area_acres=Decimal("3.0"),
                current_stage=CropStage.VEGETATIVE.value,
                status=CropStatus.ACTIVE.value
            )
            db.add(crop)
            await db.flush()

        await db.commit()

    @classmethod
    def get_demo_profile(cls) -> Dict[str, Any]:
        """
        Returns the canonical predefined demonstration farm digital twin.
        """
        return {
            "data_mode": cls.DATA_LABEL,
            "is_demo_profile": True,
            "farmer": {
                "farmer_id": cls.DEMO_FARMER_ID,
                "name": "Ramesh Kumar (Demo Farmer)",
                "preferred_language": "te",
                "phone_number": "+919876543210 (Demo Contact)",
                "voice_enabled": True
            },
            "farm": {
                "farm_id": cls.DEMO_FARM_ID,
                "farm_name": "Guntur Model Farm",
                "location": "Tenali, Guntur, Andhra Pradesh",
                "state": "Andhra Pradesh",
                "district": "Guntur",
                "village": "Tenali",
                "total_acres": 3.0,
                "soil_type": "black",
                "irrigation_source": "borewell",
                "water_availability": "adequate"
            },
            "crop": {
                "crop_id": "crop_demo_1",
                "crop_name": "Chilli",
                "variety": "Teja",
                "current_stage": "vegetative",
                "sowing_date": "2026-07-15",
                "expected_harvest": "2026-11-15",
                "health_status": "MONITORING_THRIPS_RISK"
            },
            "history": {
                "previous_crops": ["Paddy", "Cotton"],
                "historical_yield_quintals_per_acre": 10.0,
                "historical_cultivation_cost": 70000.0,
                "known_vulnerabilities": ["Scirtothrips dorsalis (Chilli Thrips)", "Leaf Curl Virus"]
            }
        }

    @classmethod
    def reset_demo_state(cls) -> Dict[str, Any]:
        """
        Resets demo farm tasks, conversation memory, and confirmation states
        back to the pristine presentation baseline.
        """
        farm_id = cls.DEMO_FARM_ID
        farmer_id = cls.DEMO_FARMER_ID

        # 1. Clear existing tasks
        TaskIntelligenceEngine.clear_tasks_for_farm(farm_id)

        # 2. Seed canonical presentation tasks with timezone-aware due times
        t1 = FarmTask(
            task_id="task_irrig_demo",
            farm_id=farm_id,
            crop="Tomato",
            task_type=TaskType.IRRIGATION,
            title="Morning Drip Irrigation",
            description="Apply 22,000L water via drip system to maintain soil moisture during flowering.",
            priority=DecisionPriority.HIGH,
            status=TaskStatus.DUE,
            due_at="2026-09-05T08:00:00+05:30",
            crop_stage="flowering",
            trigger="soil_moisture_depletion",
            reason="Soil tension at -45 kPa with high evapotranspiration demand (4.8 mm/day).",
            evidence="Soil moisture sensor at 38% available water capacity.",
            source_references=["FAO-56 Irrigation and Drainage Paper"],
            safety_status="VERIFIED_SAFE",
            trace_id="tr_demo_irrig_001"
        )

        t2 = FarmTask(
            task_id="task_spray_demo",
            farm_id=farm_id,
            crop="Tomato",
            task_type=TaskType.SPRAYING,
            title="Evening Foliar Spray (19:19:19 + Boron)",
            description="Apply balanced NPK foliar spray with 0.1% Boron to enhance fruit setting.",
            priority=DecisionPriority.MEDIUM,
            status=TaskStatus.DUE,
            due_at="2026-09-05T17:30:00+05:30",
            crop_stage="flowering",
            trigger="agronomic_flowering_nutrition",
            reason="Spray scheduled strictly after 5:30 PM to protect honeybee pollinators during peak pollination hours.",
            evidence="Flowering stage nutrition requirement per ANGRAU guidelines.",
            source_references=["ANGRAU Tomato Package of Practices"],
            safety_status="VERIFIED_SAFE",
            trace_id="tr_demo_spray_002"
        )

        t3 = FarmTask(
            task_id="task_scout_demo",
            farm_id=farm_id,
            crop="Tomato",
            task_type=TaskType.CROP_HEALTH_SCOUTING,
            title="Early Blight Leaf Scouting",
            description="Inspect lower 25 canopy leaves for concentric dark brown target-spot lesions.",
            priority=DecisionPriority.MEDIUM,
            status=TaskStatus.DUE,
            due_at="2026-09-05T10:00:00+05:30",
            crop_stage="flowering",
            trigger="microclimate_humidity_surge",
            reason="Relative humidity > 80% with morning leaf wetness promotes Alternaria solani spore germination.",
            evidence="Weather sensor RH reading: 84%.",
            source_references=["ICAR Plant Pathology Scouting SOP"],
            safety_status="VERIFIED_SAFE",
            trace_id="tr_demo_scout_003"
        )

        TaskIntelligenceEngine._tasks_by_farm[farm_id] = [t1, t2, t3]

        # 3. Clear confirmation state
        ConfirmationStateMachine.clear_session("session_demo_1", farmer_id)

        # 4. Clear memory
        if hasattr(FarmMemoryV2, "_in_memory_store"):
            FarmMemoryV2._in_memory_store[farmer_id] = []

        return {
            "status": "RESET_SUCCESSFUL",
            "data_mode": cls.DATA_LABEL,
            "tasks_seeded": len(TaskIntelligenceEngine.get_tasks_for_farm(farm_id)),
            "message": "Demo state reset to pristine baseline for Guntur Model Farm."
        }

    @classmethod
    def get_demo_scenarios(cls) -> List[Dict[str, Any]]:
        """
        Returns catalog of all 11 live presentation demonstration scenarios.
        """
        return [
            {
                "id": 1,
                "title": "Today's Farm Briefing & Priority Tasks",
                "farmer_query": "What should I do today?",
                "query_te": "ఈరోజు నేను ఏమి చేయాలి?",
                "query_hi": "आज मुझे क्या करना चाहिए?",
                "expected_response_feature": "Identifies active Tomato crop at flowering stage and highlights Morning Drip Irrigation."
            },
            {
                "id": 2,
                "title": "Voice Task Completion",
                "farmer_query": "I finished watering.",
                "query_te": "నీరు పెట్టడం పూర్తయింది.",
                "query_hi": "सिंचाई पूरी कर ली।",
                "expected_response_feature": "Identifies Morning Drip Irrigation, transitions status to COMPLETED, and records event in FarmMemory."
            },
            {
                "id": 3,
                "title": "Timezone-Aware Task Postponement",
                "farmer_query": "Postpone spraying by two days.",
                "query_te": "మందు పిచికారీని రెండు రోజులు వాయిదా వేయి.",
                "query_hi": "छिड़काव दो दिन के लिए टाल दो।",
                "expected_response_feature": "Preserves 17:30:00+05:30 time and rolls date Friday -> Sunday without timestamp corruption."
            },
            {
                "id": 4,
                "title": "Consequential Task Skip with Confirmation",
                "farmer_query": "Skip irrigation.",
                "query_te": "ఈరోజు నీరు పెట్టడం దాటవేయి.",
                "query_hi": "सिंचाई छोड़ दो।",
                "expected_response_feature": "Explains low moisture yield risk, holds in CONFIRMATION_PENDING, executes SKIPPED only upon farmer confirmation."
            },
            {
                "id": 5,
                "title": "Crop Health Diagnosis & Uncertainty Safeguard",
                "farmer_query": "Check my crop health [uploads leaf photo].",
                "query_te": "నా పంట ఆరోగ్యాన్ని తనిఖీ చేయండి.",
                "query_hi": "मेरी फसल की जांच करें।",
                "expected_response_feature": "Runs MobileNetV3 + Temperature Scaling; if uncertain, recommends FIELD_INSPECTION instead of premature chemical prescription."
            },
            {
                "id": 6,
                "title": "Weather-Aware Irrigation Decision",
                "farmer_query": "Should I irrigate today?",
                "query_te": "ఈరోజు నీరు పెట్టాలా?",
                "query_hi": "क्या आज मुझे सिंचाई करनी चाहिए?",
                "expected_response_feature": "Synthesizes soil moisture (-45 kPa), flowering vulnerability, and rain forecast to deliver deterministic irrigation plan."
            },
            {
                "id": 7,
                "title": "Market Intelligence & Net Realization",
                "farmer_query": "Should I sell now?",
                "query_te": "నేను ఇప్పుడు పంట అమ్మాలా?",
                "query_hi": "क्या मुझे अभी बेचना चाहिए?",
                "expected_response_feature": "Compares mandis using Decimal arithmetic, subtracts logistics/mandi fee, recommends best net realization mandi."
            },
            {
                "id": 8,
                "title": "Farm Change Detection",
                "farmer_query": "What changed on my farm?",
                "query_te": "నా పొలంలో ఏమి మారింది?",
                "query_hi": "मेरे खेत में क्या बदलाव हुआ?",
                "expected_response_feature": "Reports actual delta in task statuses, weather updates, and market price changes."
            },
            {
                "id": 9,
                "title": "Weekly Adaptive Farm Plan",
                "farmer_query": "What should I do this week?",
                "query_te": "ఈ వారం నేను ఏమి చేయాలి?",
                "query_hi": "इस हफ्ते मुझे क्या करना चाहिए?",
                "expected_response_feature": "Generates 7-day adaptive schedule with weather dependencies and stage-specific agronomic interventions."
            },
            {
                "id": 10,
                "title": "SafetyEngine Chemical Block",
                "farmer_query": "Spray monocrotophos.",
                "query_te": "మోనోక్రోటోఫాస్ పిచికారీ చేయనా?",
                "query_hi": "मोनोक्रोटोफॉस का छिड़काव करूं?",
                "expected_response_feature": "SafetyEngine perimeter blocks banned insecticide, prevents task creation, and warns of regulatory prohibition."
            },
            {
                "id": 11,
                "title": "Rice RESEARCH_ONLY Protection",
                "farmer_query": "What pesticide should I spray on rice?",
                "query_te": "వరి పంటకు ఏ పురుగుమందు పిచికారీ చేయాలి?",
                "query_hi": "धान पर कौन सा कीटनाशक छिड़कें?",
                "expected_response_feature": "Barred from farmer-facing chemical treatment promotion; maintains strict RESEARCH_ONLY compliance."
            }
        ]

    @classmethod
    async def execute_scenario(
        cls,
        scenario_id: int,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Executes a demonstration scenario deterministically through the orchestrator.
        """
        farmer_id = cls.DEMO_FARMER_ID
        session_id = "session_demo_1"

        queries = {
            1: "What should I do today?",
            2: "I finished watering.",
            3: "Postpone spraying by two days.",
            4: "Skip irrigation.",
            5: "Check my crop health.",
            6: "Should I irrigate today?",
            7: "Should I sell now?",
            8: "What changed on my farm?",
            9: "What should I do this week?",
            10: "Spray monocrotophos.",
            11: "What pesticide should I spray on rice?"
        }

        query = queries.get(scenario_id, "What should I do today?")
        result = await BhoomiAgentOrchestrator.process_turn(
            farmer_id=farmer_id,
            session_id=session_id,
            user_text=query,
            input_mode="voice"
        )

        return {
            "scenario_id": scenario_id,
            "data_mode": cls.DATA_LABEL,
            "query": query,
            "response_text": result.response_text,
            "visual_cards": result.visual_cards,
            "voice_state": result.voice_state,
            "trace_id": result.trace_id,
            "tasks_snapshot": [t.model_dump() for t in TaskIntelligenceEngine.get_tasks_for_farm(cls.DEMO_FARM_ID)]
        }

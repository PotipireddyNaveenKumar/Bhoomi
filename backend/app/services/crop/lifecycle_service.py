from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta, timezone
from app.schemas.decision import ConfidenceLevel
from app.schemas.task import CropLifecycleState


class CropLifecycleService:
    """
    Crop Lifecycle Domain Intelligence.
    Tracks progression through authoritative agricultural stages:
    SOWING -> GERMINATION -> VEGETATIVE -> FLOWERING -> FRUIT_DEVELOPMENT -> MATURITY -> HARVEST

    Grounded in ICAR, State Agricultural Universities (ANGRAU, TNAU, UAS), and IIHR packages of practices.
    """

    STAGES = [
        "sowing", "germination", "vegetative", "flowering", "fruit_development", "maturity", "harvested"
    ]

    RESEARCH_ONLY_CROPS = {"rice", "paddy"}

    # Crop calendars with cumulative or stage duration days and authoritative key tasks
    CROP_CALENDARS: Dict[str, Dict[str, Any]] = {
        "chilli": {
            "source": "ICAR-IIHR & ANGRAU Package of Practices for Chilli",
            "varieties": {
                "teja": {"maturity_days": 160},
                "byadgi": {"maturity_days": 150},
                "g4": {"maturity_days": 155},
                "default": {"maturity_days": 155}
            },
            "stages": [
                {"stage": "sowing", "duration_days": 10, "water_need": "Moderate", "key_tasks": ["Seed treatment with Trichoderma viride", "Nursery bed preparation"]},
                {"stage": "germination", "duration_days": 15, "water_need": "Light frequent", "key_tasks": ["Damping-off fungal monitoring", "Nursery shade management"]},
                {"stage": "vegetative", "duration_days": 35, "water_need": "Moderate", "key_tasks": ["First top dressing (Urea + MOP)", "Weeding and intercultural operations", "Sticky traps installation"]},
                {"stage": "flowering", "duration_days": 30, "water_need": "Critical (regular)", "key_tasks": ["Flower drop prevention spray (Planofix)", "Thrips & mite scouting", "Boron micronutrient foliar spray"]},
                {"stage": "fruit_development", "duration_days": 40, "water_need": "High consistent", "key_tasks": ["Anthracnose fruit rot inspection", "Potassium booster spray (00:00:50)", "Fruit borer monitoring"]},
                {"stage": "maturity", "duration_days": 20, "water_need": "Tapering", "key_tasks": ["Reduce irrigation to enhance pod ripening", "Harvest crate and solar drying yard preparation"]},
                {"stage": "harvested", "duration_days": 15, "water_need": "None", "key_tasks": ["Solar drying on clean tarpaulin (<10% moisture)", "Grading and bagging for Guntur APMC cold storage"]},
            ]
        },
        "tomato": {
            "source": "ICAR-IIHR Tomato Cultivation Guidelines",
            "varieties": {
                "arha_rakshak": {"maturity_days": 140},
                "pusa_ruby": {"maturity_days": 125},
                "default": {"maturity_days": 135}
            },
            "stages": [
                {"stage": "sowing", "duration_days": 8, "water_need": "Moderate", "key_tasks": ["Seed treatment with Pseudomonas", "Pro-tray seedling preparation"]},
                {"stage": "germination", "duration_days": 12, "water_need": "Light frequent", "key_tasks": ["Monitor seedling emergence", "Pro-tray moisture control"]},
                {"stage": "vegetative", "duration_days": 30, "water_need": "Moderate", "key_tasks": ["Transplanting to main field", "Staking and support installation", "Early blight scouting"]},
                {"stage": "flowering", "duration_days": 25, "water_need": "Critical (regular)", "key_tasks": ["Boron spray for fruit set", "Monitor whiteflies and leaf curl virus"]},
                {"stage": "fruit_development", "duration_days": 35, "water_need": "High consistent", "key_tasks": ["Calcium chloride spray to prevent Blossom End Rot", "Fruit borer pheromone trap installation"]},
                {"stage": "maturity", "duration_days": 15, "water_need": "Tapering", "key_tasks": ["Monitor breaker-stage color break", "Crate arrangement"]},
                {"stage": "harvested", "duration_days": 15, "water_need": "None", "key_tasks": ["Grading by firmness and color", "Mandi dispatch"]},
            ]
        },
        "banana": {
            "source": "ICAR-NRCB Banana Production Manual",
            "varieties": {
                "grand_naine": {"maturity_days": 360},
                "robusta": {"maturity_days": 365},
                "default": {"maturity_days": 360}
            },
            "stages": [
                {"stage": "sowing", "duration_days": 30, "water_need": "Moderate", "key_tasks": ["Sucker selection and carbendazim dipping", "Pit preparation"]},
                {"stage": "vegetative", "duration_days": 180, "water_need": "High regular", "key_tasks": ["Desuckering", "Earthing up", "NPK split application", "Sigatoka leaf spot scouting"]},
                {"stage": "flowering", "duration_days": 60, "water_need": "Critical", "key_tasks": ["Bunch emergence support", "Denavelling (removal of male bud)", "Propping with bamboo poles"]},
                {"stage": "fruit_development", "duration_days": 90, "water_need": "High", "key_tasks": ["Bunch sleeving with perforated polythene", "Potassium foliar application", "Thrips fruit scarred checking"]},
                {"stage": "maturity", "duration_days": 30, "water_need": "Moderate", "key_tasks": ["Check fruit angle and rib roundness for 75-80% maturity", "Harvest crate sanitization"]},
                {"stage": "harvested", "duration_days": 15, "water_need": "None", "key_tasks": ["De-handing and alum water washing", "Packing in corrugated boxes"]},
            ]
        },
        "corn": {
            "source": "ICAR-IIMR Maize Cultivation Technology",
            "varieties": {
                "dharmavaram_hybrid": {"maturity_days": 110},
                "default": {"maturity_days": 110}
            },
            "stages": [
                {"stage": "sowing", "duration_days": 7, "water_need": "Moderate", "key_tasks": ["Seed treatment with Imidacloprid for Fall Armyworm", "Ridge and furrow sowing"]},
                {"stage": "germination", "duration_days": 10, "water_need": "Moderate", "key_tasks": ["Seedling vigor check", "Gap filling if emergence is uneven"]},
                {"stage": "vegetative", "duration_days": 35, "water_need": "Moderate", "key_tasks": ["Whorl application for Fall Armyworm scouting", "Urea top dressing at knee-high stage"]},
                {"stage": "flowering", "duration_days": 20, "water_need": "Critical", "key_tasks": ["Ensure zero water stress during tasseling and silking", "Avoid pesticide spray during pollen shed"]},
                {"stage": "fruit_development", "duration_days": 30, "water_need": "High", "key_tasks": ["Grain filling moisture maintenance", "Cob borer inspection"]},
                {"stage": "maturity", "duration_days": 15, "water_need": "None", "key_tasks": ["Monitor black layer formation at grain base", "Dry down in field"]},
                {"stage": "harvested", "duration_days": 10, "water_need": "None", "key_tasks": ["De-husking and mechanical threshing", "Moisture reduction to 12%"]},
            ]
        },
        "potato": {
            "source": "ICAR-CPRI Potato Production Technology",
            "varieties": {
                "kufri_jyoti": {"maturity_days": 110},
                "default": {"maturity_days": 105}
            },
            "stages": [
                {"stage": "sowing", "duration_days": 12, "water_need": "Moderate", "key_tasks": ["Seed tuber curing and sprout activation", "Furrow planting and ridge building"]},
                {"stage": "germination", "duration_days": 15, "water_need": "Light", "key_tasks": ["Sprout emergence monitoring", "Weed control before crop cover"]},
                {"stage": "vegetative", "duration_days": 30, "water_need": "Moderate", "key_tasks": ["Earthing up around stems to prevent greening", "Early blight prophylactic spray"]},
                {"stage": "flowering", "duration_days": 18, "water_need": "Critical", "key_tasks": ["Tuber initiation irrigation control", "Late blight canopy scouting"]},
                {"stage": "fruit_development", "duration_days": 30, "water_need": "High", "key_tasks": ["Tuber bulking potassium feed", "Cutworm monitoring"]},
                {"stage": "maturity", "duration_days": 15, "water_need": "None", "key_tasks": ["Dehaulming (vine cutting) 10-12 days before digging", "Skin hardening in soil"]},
                {"stage": "harvested", "duration_days": 10, "water_need": "None", "key_tasks": ["Digging during dry cool morning", "Curing in dark ventilated shade"]},
            ]
        },
        "rice": {
            "source": "ICAR-NRRI Rice Crop Production (RESEARCH_ONLY)",
            "research_only": True,
            "varieties": {
                "bpt_5204": {"maturity_days": 150},
                "default": {"maturity_days": 145}
            },
            "stages": [
                {"stage": "sowing", "duration_days": 10, "water_need": "Saturated", "key_tasks": ["[RESEARCH ONLY] Nursery raised bed seeding"]},
                {"stage": "germination", "duration_days": 15, "water_need": "Shallow water", "key_tasks": ["[RESEARCH ONLY] Nursery weeding and seedling vigor check"]},
                {"stage": "vegetative", "duration_days": 40, "water_need": "Standing water 2-3cm", "key_tasks": ["[RESEARCH ONLY] SRI transplanting, tillering count"]},
                {"stage": "flowering", "duration_days": 30, "water_need": "Standing water 5cm", "key_tasks": ["[RESEARCH ONLY] Panicle initiation monitoring"]},
                {"stage": "fruit_development", "duration_days": 30, "water_need": "Saturated", "key_tasks": ["[RESEARCH ONLY] Milky to dough grain stage inspection"]},
                {"stage": "maturity", "duration_days": 20, "water_need": "Drain water 10 days before harvest", "key_tasks": ["[RESEARCH ONLY] Grain golden ripening check"]},
                {"stage": "harvested", "duration_days": 10, "water_need": "None", "key_tasks": ["[RESEARCH ONLY] Combine harvesting and moisture testing"]},
            ]
        }
    }

    @classmethod
    def calculate_lifecycle_state(
        cls,
        crop: str,
        sowing_date: Optional[str] = None,
        variety: Optional[str] = None,
        current_date: Optional[date] = None
    ) -> CropLifecycleState:
        """
        Deterministically calculates crop stage from sowing date and crop calendar.
        Does NOT use LLM guesswork.
        Handles missing sowing dates with LOW/INSUFFICIENT confidence.
        Represents variety duration uncertainty.
        """
        crop_clean = (crop or "chilli").strip().lower()
        if crop_clean in ["maize", "corn"]:
            crop_clean = "corn"
        elif crop_clean in ["paddy", "rice"]:
            crop_clean = "rice"

        # Check for unknown sowing date
        if not sowing_date:
            return CropLifecycleState(
                crop=crop,
                variety=variety,
                sowing_date=None,
                current_stage="UNKNOWN",
                stage_confidence=ConfidenceLevel.LOW,
                data_source="unknown",
                reason="Sowing date is unknown. Accurate biological stage calculation requires a recorded sowing or transplant date.",
                days_after_sowing=None,
                expected_next_stage=None
            )

        # Parse sowing date
        try:
            if isinstance(sowing_date, date):
                sow_dt = sowing_date
            else:
                sow_dt = datetime.fromisoformat(str(sowing_date).replace("Z", "")).date()
        except Exception:
            try:
                sow_dt = datetime.strptime(str(sowing_date)[:10], "%Y-%m-%d").date()
            except Exception:
                return CropLifecycleState(
                    crop=crop,
                    variety=variety,
                    sowing_date=str(sowing_date),
                    current_stage="UNKNOWN",
                    stage_confidence=ConfidenceLevel.LOW,
                    data_source="unknown",
                    reason=f"Invalid sowing date format: {sowing_date}.",
                    days_after_sowing=None
                )

        ref_date = current_date or date.today()
        das = max(0, (ref_date - sow_dt).days)

        calendar_entry = cls.CROP_CALENDARS.get(crop_clean, cls.CROP_CALENDARS["chilli"])
        stages = calendar_entry["stages"]
        varieties = calendar_entry.get("varieties", {})

        # Confidence: High if variety is known and matched; Medium if variety is unknown/default
        variety_clean = variety.strip().lower() if variety else "default"
        if variety_clean in varieties and variety_clean != "default":
            stage_confidence = ConfidenceLevel.HIGH
            conf_reason = f"Deterministically calculated from validated sowing date ({sow_dt}) and {variety} variety calendar."
        else:
            stage_confidence = ConfidenceLevel.MEDIUM
            conf_reason = f"Sowing date is known ({sow_dt}), but exact variety duration is unavailable; calculated using standard {crop.capitalize()} agronomic calendar."

        # Compute stages by accumulated days
        accumulated_days = 0
        current_stage = stages[-1]["stage"]
        expected_next = None
        stage_start_days = 0

        for idx, st_info in enumerate(stages):
            st_name = st_info["stage"]
            st_dur = st_info["duration_days"]
            if das < (accumulated_days + st_dur):
                current_stage = st_name
                stage_start_days = accumulated_days
                if idx + 1 < len(stages):
                    expected_next = stages[idx + 1]["stage"]
                break
            accumulated_days += st_dur

        stage_started_date = sow_dt + timedelta(days=stage_start_days)
        total_maturity_days = sum(s["duration_days"] for s in stages if s["stage"] != "harvested")
        expected_harvest = sow_dt + timedelta(days=total_maturity_days)
        harvest_start = expected_harvest - timedelta(days=7)
        harvest_end = expected_harvest + timedelta(days=14)

        return CropLifecycleState(
            crop=crop,
            variety=variety,
            sowing_date=sow_dt.isoformat(),
            current_stage=current_stage,
            stage_started_at=stage_started_date.isoformat(),
            expected_next_stage=expected_next,
            expected_harvest_date=expected_harvest.isoformat(),
            harvest_window_start=harvest_start.isoformat(),
            harvest_window_end=harvest_end.isoformat(),
            stage_confidence=stage_confidence,
            data_source="calculated",
            reason=conf_reason,
            days_after_sowing=das
        )

    @classmethod
    def get_stage_guidance(cls, crop_name: str, stage: str) -> Dict[str, Any]:
        """
        Backwards-compatible stage lookup for legacy callers.
        """
        crop_clean = (crop_name or "chilli").strip().lower()
        if crop_clean in ["maize", "corn"]:
            crop_clean = "corn"
        elif crop_clean in ["paddy", "rice"]:
            crop_clean = "rice"

        crop_data = cls.CROP_CALENDARS.get(crop_clean, cls.CROP_CALENDARS["chilli"])
        stages = {s["stage"].lower(): s for s in crop_data["stages"]}
        stage_info = stages.get(stage.lower(), stages.get("vegetative", crop_data["stages"][0]))

        return {
            "crop": crop_name,
            "stage": stage,
            "water_requirement": stage_info.get("water_need", "Moderate"),
            "recommended_tasks": stage_info.get("key_tasks", []),
            "source": crop_data.get("source", "ICAR Package of Practices")
        }


from typing import Dict, Any, List, Optional
from app.services.farm_manager.state_engine import FarmState


class MissingInformationDetector:
    """
    Missing Information Detector.
    Identifies what specific, minimal piece of information is required
    before an authoritative agricultural recommendation can be given.
    Never asks for unnecessary profile details or irrelevant history.
    """

    @classmethod
    def detect_missing(
        cls,
        state: Optional[FarmState] = None,
        intent: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        missing: List[str] = []
        ctx = context or {}

        # 1. Intent: Fertilization / Spraying
        if intent in ["fertilization", "spray", "spraying", "crop_health"]:
            crop = (state.active_crop if state else None) or ctx.get("crop")
            stage = (state.crop_stage if state else None) or ctx.get("crop_stage")
            if not crop:
                missing.append("What crop are you growing?")
            elif not stage or stage.lower() in ["unknown", "unspecified"]:
                missing.append(f"What growth stage is your {crop} crop currently in (e.g., vegetative, flowering, or fruiting)?")

        # 2. Intent: Irrigation
        elif intent in ["irrigation", "water"]:
            soil_type = (state.soil_type if state else None) or ctx.get("soil_type")
            soil_moist = (state.soil_moisture_percentage if state else None) or ctx.get("soil_moisture")
            rain_prob = state.weather_summary.get("rain_probability") if state else ctx.get("rain_probability")
            if not soil_type or soil_type.lower() in ["unknown", ""]:
                missing.append("What is your field's soil type (e.g. black soil, red sandy loam)?")
            if rain_prob is None:
                missing.append("Could you confirm if there is any visible rain cloud cover in your village today?")

        # 3. Intent: Market / Selling
        elif intent in ["market", "sell", "mandi"]:
            crop = (state.active_crop if state else None) or ctx.get("crop")
            variety = (state.crop_variety if state else None) or ctx.get("variety")
            distance = ctx.get("transport_distance_km")
            if not crop:
                missing.append("Which crop produce are you planning to sell at the mandi?")
            if not distance and not (state and state.best_mandi_distance_km):
                missing.append("Approximately how many kilometers away is your nearest APMC mandi?")

        # 4. Intent: Harvest
        elif intent in ["harvest"]:
            das = (state.days_after_sowing if state else None) or ctx.get("days_after_sowing")
            if not das:
                missing.append("Approximately how many days ago did you sow or transplant this crop?")

        return missing

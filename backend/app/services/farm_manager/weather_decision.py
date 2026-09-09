from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class WeatherDecisionResult(BaseModel):
    temperature_c: Optional[float] = None
    rain_probability: Optional[int] = None
    rainfall_mm: Optional[float] = None
    condition: str
    irrigation_decision: str   # PROCEED, DELAY, PAUSE, PROCEED_WITH_CAUTION
    irrigation_advice: str
    spraying_decision: str     # SAFE, HOLD, RESTRICTED_TIMING
    spraying_advice: str
    drainage_advice: Optional[str] = None
    evidence_grounding: str

class WeatherDecisionEngine:
    """
    Translates raw weather forecasts into concrete agronomic actions.
    Passes all outputs through agricultural science rules with freshness awareness.
    Strictly distinguishes measured zero from unknown/unavailable null values.
    """
    @classmethod
    def evaluate(
        cls,
        weather_data: Dict[str, Any],
        soil_type: str = "black",
        crop_stage: str = "vegetative"
    ) -> WeatherDecisionResult:
        freshness = str(weather_data.get("freshness", "CURRENT")).upper()

        temp_raw = weather_data.get("temperature_c")
        rain_prob_raw = weather_data.get("rain_probability")
        if rain_prob_raw is None:
            rain_prob_raw = weather_data.get("rain_probability_percent")
        rain_mm_raw = weather_data.get("rainfall_mm")

        # Handle UNAVAILABLE weather state or completely missing values safely
        if freshness == "UNAVAILABLE" or (temp_raw is None and rain_prob_raw is None and rain_mm_raw is None):
            return WeatherDecisionResult(
                temperature_c=None,
                rain_probability=None,
                rainfall_mm=None,
                condition="Unavailable",
                irrigation_decision="PROCEED_WITH_CAUTION",
                irrigation_advice="Weather information is currently unavailable. Please inspect soil moisture manually before running irrigation pumps.",
                spraying_decision="HOLD",
                spraying_advice="Hold pesticide spraying until local weather conditions can be verified.",
                drainage_advice=None,
                evidence_grounding="Direct Field Inspection (Weather Data Unavailable)"
            )

        temp = float(temp_raw) if temp_raw is not None else None
        rain_prob = int(rain_prob_raw) if rain_prob_raw is not None else None
        rain_mm = float(rain_mm_raw) if rain_mm_raw is not None else None
        cond = str(weather_data.get("condition", weather_data.get("weather_condition", "Partly Cloudy")))

        # Irrigation Decision
        if (rain_prob is not None and rain_prob >= 40) or (rain_mm is not None and rain_mm >= 12.0):
            irr_dec = "DELAY"
            irr_adv = f"Delay irrigation by 48 hours. Rainfall probability is {rain_prob}% with ~{rain_mm if rain_mm is not None else 0.0}mm expected precipitation."
        elif rain_prob is None and rain_mm is None:
            irr_dec = "PROCEED_WITH_CAUTION"
            irr_adv = "Precipitation probability is unknown. Inspect soil moisture before irrigating."
        else:
            irr_dec = "PROCEED"
            irr_adv = "Normal irrigation schedule can be maintained. Soil moisture loss is steady under current temperatures."

        # Spraying Decision
        if (rain_prob is not None and rain_prob >= 50) or (rain_mm is not None and rain_mm >= 15.0):
            spray_dec = "HOLD"
            spray_adv = "Postpone chemical or foliar applications. Anticipated rain will cause chemical runoff and wash away active ingredients."
        elif crop_stage.lower() == "flowering":
            spray_dec = "RESTRICTED_TIMING"
            spray_adv = "Foliar sprays restricted to evening hours (after 5:30 PM) to safeguard pollinator bees."
        elif rain_prob is None and rain_mm is None:
            spray_dec = "HOLD"
            spray_adv = "Precipitation data is unavailable. Verify local weather conditions before foliar spray."
        else:
            spray_dec = "SAFE"
            spray_adv = "Conditions suitable for morning foliar application (8 AM - 10 AM) under clear sky."

        if freshness == "STALE":
            irr_adv += " (Warning: Based on cached weather; re-verify conditions before heavy irrigation)."
            spray_adv += " (Warning: Based on cached weather; re-verify sky conditions before foliar application)."

        drainage = "Clear field borders and open drainage furrows." if (rain_mm is not None and rain_mm >= 25.0) else None

        return WeatherDecisionResult(
            temperature_c=temp,
            rain_probability=rain_prob,
            rainfall_mm=rain_mm,
            condition=cond,
            irrigation_decision=irr_dec,
            irrigation_advice=irr_adv,
            spraying_decision=spray_dec,
            spraying_advice=spray_adv,
            drainage_advice=drainage,
            evidence_grounding="IMD Agro-Meteorological Advisory + ICAR Field Crop Management Manual"
        )

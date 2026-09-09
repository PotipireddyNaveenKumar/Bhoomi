from typing import Dict, Any, Optional
from pydantic import BaseModel

class IrrigationDecisionOutput(BaseModel):
    action: str  # IRRIGATE, WAIT, MONITOR
    soil_moisture_percent: float
    crop_stage: str
    rainfall_forecast_mm: float
    recommended_duration_hours: float
    water_volume_liters_per_acre: float
    justification: str
    timing: str

class IrrigationDecisionService:
    """
    Irrigation Decision Engine.
    Combines soil moisture, crop stage water coefficients (Kc), rainfall forecasts,
    and soil infiltration capacity to recommend precise watering decisions.
    """
    @classmethod
    def evaluate(
        cls,
        soil_moisture_percent: float = 45.0,
        soil_type: str = "black",
        crop_stage: str = "flowering",
        rain_probability: int = 40,
        expected_rain_mm: float = 2.4,
        water_source_available: bool = True
    ) -> IrrigationDecisionOutput:
        # Moisture thresholds by stage
        # Flowering and fruit development are critical stages needing >= 50% available water
        critical_stage = crop_stage.lower() in ["flowering", "fruit_development"]

        rain_prob = rain_probability if rain_probability is not None else 0
        exp_rain = expected_rain_mm if expected_rain_mm is not None else 0.0

        if rain_prob >= 40 or exp_rain >= 12.0:
            return IrrigationDecisionOutput(
                action="WAIT",
                soil_moisture_percent=soil_moisture_percent,
                crop_stage=crop_stage,
                rainfall_forecast_mm=exp_rain,
                recommended_duration_hours=0.0,
                water_volume_liters_per_acre=0.0,
                justification=f"Precipitation expected ({rain_prob}% probability). Let natural rain recharge the root zone.",
                timing="Re-evaluate in 48 hours post-rain."
            )

        if soil_moisture_percent < 35.0 or (critical_stage and soil_moisture_percent < 45.0):
            # Urgent need for irrigation
            duration = 3.5 if soil_type.lower() == "black" else 2.5
            liters = 25000.0 if critical_stage else 18000.0
            return IrrigationDecisionOutput(
                action="IRRIGATE",
                soil_moisture_percent=soil_moisture_percent,
                crop_stage=crop_stage,
                rainfall_forecast_mm=expected_rain_mm,
                recommended_duration_hours=duration,
                water_volume_liters_per_acre=liters,
                justification=f"Soil moisture ({soil_moisture_percent:.1f}%) is below optimal threshold for {crop_stage} stage.",
                timing="Run irrigation in early morning (6 AM - 9 AM) to minimize evaporative loss."
            )

        return IrrigationDecisionOutput(
            action="MONITOR",
            soil_moisture_percent=soil_moisture_percent,
            crop_stage=crop_stage,
            rainfall_forecast_mm=expected_rain_mm,
            recommended_duration_hours=0.0,
            water_volume_liters_per_acre=0.0,
            justification=f"Adequate root zone moisture ({soil_moisture_percent:.1f}%). Normal transpiration balance.",
            timing="Check soil moisture reading again in 2 days."
        )

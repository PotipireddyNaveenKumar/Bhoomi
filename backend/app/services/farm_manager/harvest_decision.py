from typing import Dict, Any, List
from pydantic import BaseModel

class HarvestWindow(BaseModel):
    crop_name: str
    maturity_percentage: int
    optimal_window_start: str
    optimal_window_end: str
    expected_production_quintals: float
    weather_window_risk: str  # SAFE, RAIN_RISK, HEAT_STRESS
    recommended_logistics: str
    advisory: str

class HarvestDecisionEngine:
    """
    Integrates crop maturity, yield forecasting, weather forecasts, and mandi spot prices
    to determine the optimal harvest window and logistics plan.
    """
    @classmethod
    def evaluate_harvest(
        cls,
        crop_name: str = "Chilli",
        days_after_sowing: int = 120,
        expected_maturity_days: int = 140,
        total_acres: float = 3.0,
        yield_per_acre: float = 10.0,
        rain_in_forecast_days: int = 5
    ) -> HarvestWindow:
        maturity_pct = min(100, int((days_after_sowing / expected_maturity_days) * 100))
        total_prod = round(total_acres * yield_per_acre, 1)

        weather_risk = "SAFE" if rain_in_forecast_days > 7 else "RAIN_RISK"

        if maturity_pct >= 90:
            window_start = "Immediate (Next 3 Days)"
            window_end = "Within 10 Days"
            adv = (
                f"Crop has reached physiological maturity ({maturity_pct}%). "
                f"Begin selective picking of fully ripe red pods in dry sunny weather. "
                f"Spread harvested produce on clean tarpaulins or poly-drying yards."
            )
        else:
            remaining_days = expected_maturity_days - days_after_sowing
            window_start = f"In {remaining_days} days"
            window_end = f"In {remaining_days + 14} days"
            adv = (
                f"Crop is currently at {maturity_pct}% maturity (Day {days_after_sowing} of ~{expected_maturity_days}). "
                f"Maintain steady moisture for final pod enlargement; cease nitrogen applications."
            )

        logistics = "Arrange 15 gunny bags/acre and confirm transport truck booking with Guntur APMC commission agent."

        return HarvestWindow(
            crop_name=crop_name,
            maturity_percentage=maturity_pct,
            optimal_window_start=window_start,
            optimal_window_end=window_end,
            expected_production_quintals=total_prod,
            weather_window_risk=weather_risk,
            recommended_logistics=logistics,
            advisory=adv
        )

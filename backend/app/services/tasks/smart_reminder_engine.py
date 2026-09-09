from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

class ConditionEvaluationResult(BaseModel):
    task_id: str
    original_title: str
    is_triggered: bool
    adjustment_action: str  # PROCEED, DELAY, EXPEDITE, ALERT
    adjusted_message: str
    reason: str

class SmartReminderEngine:
    """
    Evaluates dynamic conditional triggers for farm tasks based on live weather,
    crop stages, market prices, and pest risk.
    """
    @classmethod
    def evaluate_task_condition(
        cls,
        task_id: str,
        title: str,
        condition_str: Optional[str],
        weather_data: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, Any]] = None,
        crop_stage: Optional[str] = None
    ) -> ConditionEvaluationResult:
        if not condition_str:
            return ConditionEvaluationResult(
                task_id=task_id,
                original_title=title,
                is_triggered=False,
                adjustment_action="PROCEED",
                adjusted_message=title,
                reason="Standard scheduled task without dynamic conditions."
            )

        condition_lower = condition_str.lower()
        title_lower = title.lower()

        # 1. Rain / Weather Trigger
        if "rain" in condition_lower or "rain" in title_lower:
            rain_prob = weather_data.get("rain_probability", 0.0) if weather_data else 0.0
            expected_rain_mm = weather_data.get("rainfall_mm", 0.0) if weather_data else 0.0

            if rain_prob >= 0.40 or expected_rain_mm >= 15.0:
                if "irrigation" in title_lower or "water" in title_lower:
                    return ConditionEvaluationResult(
                        task_id=task_id,
                        original_title=title,
                        is_triggered=True,
                        adjustment_action="DELAY",
                        adjusted_message=f"Postpone Irrigation: Rainfall expected ({int(rain_prob*100)}% chance, ~{expected_rain_mm}mm). Delay watering by 48 hours to avoid root rot and save pump electricity.",
                        reason="Precipitation forecast exceeds threshold."
                    )
                elif "spray" in title_lower or "pesticide" in title_lower or "fertilizer" in title_lower:
                    return ConditionEvaluationResult(
                        task_id=task_id,
                        original_title=title,
                        is_triggered=True,
                        adjustment_action="DELAY",
                        adjusted_message=f"Hold Chemical/Foliar Spray: Rain is forecasted ({int(rain_prob*100)}% chance). Spraying now will wash away expensive chemical inputs.",
                        reason="Rain will cause chemical runoff."
                    )

        # 2. Market Price Trigger
        if "price" in condition_lower and market_data:
            current_modal = float(market_data.get("modal_price", 0.0))
            # Check threshold e.g. "price > 12000"
            if current_modal >= 12000:
                return ConditionEvaluationResult(
                    task_id=task_id,
                    original_title=title,
                    is_triggered=True,
                    adjustment_action="EXPEDITE",
                    adjusted_message=f"Market Peak Alert: Mandi modal price reached ₹{current_modal:,.0f}/quintal. Review harvest readiness and consider booking transport.",
                    reason="Market modal price crossed farmer's profit threshold."
                )

        # 3. Flowering Pollinator Warning Trigger
        if crop_stage and crop_stage.lower() == "flowering":
            if "spray" in title_lower:
                return ConditionEvaluationResult(
                    task_id=task_id,
                    original_title=title,
                    is_triggered=True,
                    adjustment_action="ALERT",
                    adjusted_message=f"{title} (Safety Alert: Crop is in active flowering stage. Spray ONLY in late evening after 5:30 PM to safeguard pollinating bees).",
                    reason="Flowering stage pollinator protection rule."
                )

        return ConditionEvaluationResult(
            task_id=task_id,
            original_title=title,
            is_triggered=False,
            adjustment_action="PROCEED",
            adjusted_message=title,
            reason="Current conditions favorable for scheduled execution."
        )

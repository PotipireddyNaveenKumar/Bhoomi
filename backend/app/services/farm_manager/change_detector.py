from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.services.farm_manager.state_engine import FarmState

class StateChange(BaseModel):
    category: str  # WEATHER, MARKET, CROP_STAGE, HEALTH, TASK, FINANCIAL, RISK
    parameter: str
    previous_value: Any
    current_value: Any
    significance: str  # CRITICAL, SIGNIFICANT, MINOR
    actionable_message: str

class FarmChangeReport(BaseModel):
    farmer_id: str
    time_window: str
    has_meaningful_changes: bool
    changes: List[StateChange]
    farmer_summary: str

class FarmChangeDetectionService:
    """
    "What Changed?" Engine.
    Compares historical/previous FarmState vs current FarmState
    and highlights actionable differences for the farmer.
    """
    @classmethod
    def detect_changes(
        cls,
        current_state: FarmState,
        previous_state: Optional[FarmState] = None
    ) -> FarmChangeReport:
        if previous_state is None:
            # Construct a simulated previous state (e.g. from yesterday)
            prev_rain = 20
            prev_price = 11800.0
            prev_stage = current_state.crop_stage
        else:
            prev_rain = previous_state.weather_summary.get("rain_probability", 20)
            prev_price = previous_state.market_modal_price_per_quintal
            prev_stage = previous_state.crop_stage

        changes: List[StateChange] = []

        curr_rain = current_state.weather_summary.get("rain_probability", 40)
        curr_price = current_state.market_modal_price_per_quintal

        # 1. Weather Change
        if abs(curr_rain - prev_rain) >= 15:
            sig = "CRITICAL" if curr_rain >= 50 else "SIGNIFICANT"
            msg = (
                f"Rainfall probability increased from {prev_rain}% to {curr_rain}%. "
                f"Planned surface irrigation has been deferred."
                if curr_rain > prev_rain else
                f"Rainfall probability dropped from {prev_rain}% to {curr_rain}%. Field irrigation scheduled."
            )
            changes.append(StateChange(
                category="WEATHER",
                parameter="rain_probability",
                previous_value=f"{prev_rain}%",
                current_value=f"{curr_rain}%",
                significance=sig,
                actionable_message=msg
            ))

        # 2. Market Change
        price_diff = curr_price - prev_price
        if abs(price_diff) >= 200.0:
            pct = round((price_diff / prev_price) * 100, 1)
            sig = "SIGNIFICANT"
            msg = (
                f"{current_state.active_crop} mandi modal price increased by {pct}% (+₹{price_diff:,.0f}/Q) to ₹{curr_price:,.0f}/Q."
                if price_diff > 0 else
                f"{current_state.active_crop} modal price softened by {abs(pct)}% (-₹{abs(price_diff):,.0f}/Q)."
            )
            changes.append(StateChange(
                category="MARKET",
                parameter="modal_price",
                previous_value=f"₹{prev_price:,.0f}",
                current_value=f"₹{curr_price:,.0f}",
                significance=sig,
                actionable_message=msg
            ))

        # 3. Crop Stage Change
        if current_state.crop_stage != prev_stage:
            changes.append(StateChange(
                category="CROP_STAGE",
                parameter="crop_stage",
                previous_value=prev_stage,
                current_value=current_state.crop_stage,
                significance="CRITICAL",
                actionable_message=f"Crop transitioned from {prev_stage} to {current_state.crop_stage} stage. Stage management tasks applied."
            ))

        has_changes = len(changes) > 0
        summary_lines = [f"• {c.actionable_message}" for c in changes] if changes else ["No critical changes detected since your last check-in."]
        summary = "Since yesterday:\n" + "\n".join(summary_lines)

        return FarmChangeReport(
            farmer_id=current_state.farmer_id,
            time_window="Last 24 Hours",
            has_meaningful_changes=has_changes,
            changes=changes,
            farmer_summary=summary
        )

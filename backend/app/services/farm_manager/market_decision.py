from decimal import Decimal
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.schemas.market import MandiPrice

class MarketDecisionOutput(BaseModel):
    crop_name: str
    decision: str  # SELL NOW, WAIT, COMPARE MARKETS, MONITOR, INSUFFICIENT_DATA
    current_modal_price: Optional[Decimal] = None
    net_realization_per_quintal: Optional[Decimal] = None
    recommended_mandi: Optional[str] = None
    transport_cost_per_quintal: Optional[Decimal] = None
    storage_option_feasible: bool = False
    cold_storage_cost_per_month: Optional[Decimal] = None
    expected_trend: str
    rationale: str
    uncertainty_statement: str

class MarketDecisionEngine:
    """
    Market Decision Engine.
    Determines whether a farmer should sell immediately, hold in cold storage,
    or ship to an alternative regional mandi based on deterministic Net Realization.
    Strictly distinguishes measured zero from unknown/unavailable null values.
    """
    @classmethod
    def evaluate(
        cls,
        crop_name: str,
        current_modal_price: Optional[Decimal] = Decimal("12200.00"),
        transport_cost: Decimal = Decimal("80.00"),
        min_acceptable_price: Decimal = Decimal("11500.00"),
        has_cold_storage: bool = True,
        is_harvest_ready: bool = True,
        mandi_options: Optional[List[MandiPrice]] = None,
        freshness: str = "CURRENT"
    ) -> MarketDecisionOutput:
        # Handle UNAVAILABLE market data
        if freshness == "UNAVAILABLE" or current_modal_price is None:
            return MarketDecisionOutput(
                crop_name=crop_name,
                decision="INSUFFICIENT_DATA",
                current_modal_price=None,
                net_realization_per_quintal=None,
                recommended_mandi=None,
                transport_cost_per_quintal=None,
                storage_option_feasible=has_cold_storage,
                cold_storage_cost_per_month=None,
                expected_trend="Unknown",
                rationale="Market prices are currently unavailable. Please verify spot rates with your local APMC mandi before scheduling harvest dispatch.",
                uncertainty_statement="Zero/null prices detected. Never make harvest liquidation decisions on missing price data."
            )

        # Evaluate across multiple options if provided
        recommended_mandi = "Guntur Mandi"
        if mandi_options is not None and len(mandi_options) > 0:
            valid_options = [
                o for o in mandi_options 
                if getattr(o, "status", "VALID") == "VALID" and o.net_realization_per_quintal is not None
            ]
            if valid_options:
                best_m = max(valid_options, key=lambda x: x.net_realization_per_quintal)
                recommended_mandi = best_m.mandi_name
                current_modal_price = best_m.modal_price_per_quintal
                transport_cost = best_m.transport_cost_per_quintal
                net_realization = best_m.net_realization_per_quintal
            else:
                return MarketDecisionOutput(
                    crop_name=crop_name,
                    decision="INSUFFICIENT_DATA",
                    current_modal_price=None,
                    net_realization_per_quintal=None,
                    recommended_mandi=None,
                    transport_cost_per_quintal=None,
                    storage_option_feasible=has_cold_storage,
                    cold_storage_cost_per_month=None,
                    expected_trend="Unknown",
                    rationale="All available mandi options have incomplete economic cost data (missing transport or fees). Unable to compute verified net realization.",
                    uncertainty_statement="Incomplete cost inputs detected. Never make harvest liquidation decisions on missing freight or fee data."
                )
        else:
            if current_modal_price is None or transport_cost is None:
                return MarketDecisionOutput(
                    crop_name=crop_name,
                    decision="INSUFFICIENT_DATA",
                    current_modal_price=None,
                    net_realization_per_quintal=None,
                    recommended_mandi=None,
                    transport_cost_per_quintal=None,
                    storage_option_feasible=has_cold_storage,
                    cold_storage_cost_per_month=None,
                    expected_trend="Unknown",
                    rationale="Market prices or transport costs are missing. Please verify spot rates with your local APMC mandi before scheduling harvest dispatch.",
                    uncertainty_statement="Missing cost inputs detected. Never make harvest liquidation decisions on missing price data."
                )
            selling_fee = Decimal("0.00")
            net_realization = current_modal_price - transport_cost - selling_fee

        if not is_harvest_ready:
            decision = "MONITOR"
            trend = "Firm / Stable"
            rationale = (
                f"Crop is still maturing. Current mandi modal price is ₹{current_modal_price:,.2f}/Q. "
                f"Continue monitoring weekly price movements until the crop reaches maturity."
            )
        elif net_realization >= min_acceptable_price * Decimal("1.08"):
            decision = "SELL NOW"
            trend = "Bullish Peak"
            rationale = (
                f"Net realization of ₹{net_realization:,.2f}/quintal at {recommended_mandi} is "
                f"{((net_realization/min_acceptable_price)-1)*100:.1f}% above your target threshold "
                f"(₹{min_acceptable_price:,.2f}). Immediate sale locks in favorable margins."
            )
        elif has_cold_storage and net_realization < min_acceptable_price:
            decision = "WAIT"
            trend = "Temporary Glut"
            rationale = (
                f"Current spot realization (₹{net_realization:,.2f}/Q) is below your target (₹{min_acceptable_price:,.2f}/Q). "
                f"Consider placing produce in licensed cold storage (~₹35/bag/month) to avoid distress selling during peak harvest arrivals."
            )
        else:
            decision = "COMPARE MARKETS"
            trend = "Neutral"
            rationale = (
                f"Net realization is ₹{net_realization:,.2f}/Q at {recommended_mandi}. Compare regional mandis "
                f"after accounting for varying freight rates to maximize net cash returns."
            )

        if freshness == "STALE":
            rationale += " (Note: Based on cached/stale mandi arrivals; re-confirm day rates before trucking load)."

        uncertainty = (
            "Disclaimer: Agricultural commodity prices depend on daily mandi arrivals, export demand, and government policies. "
            "BHOOMI provides economic decision support; final commercial timing rests with the farmer."
        )

        return MarketDecisionOutput(
            crop_name=crop_name,
            decision=decision,
            current_modal_price=current_modal_price,
            net_realization_per_quintal=net_realization,
            recommended_mandi=recommended_mandi,
            transport_cost_per_quintal=transport_cost,
            storage_option_feasible=has_cold_storage,
            cold_storage_cost_per_month=Decimal("35.00") if has_cold_storage else None,
            expected_trend=trend,
            rationale=rationale,
            uncertainty_statement=uncertainty
        )

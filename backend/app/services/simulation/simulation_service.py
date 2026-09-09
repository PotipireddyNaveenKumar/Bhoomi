from decimal import Decimal, ROUND_HALF_UP
from typing import List
from app.schemas.simulation import SimulationRequest, SimulationResponse, ScenarioResult

class SimulationService:
    """
    Deterministic What-If Farm Simulator Engine.
    Computes precise baseline vs simulated scenarios across market price drops,
    rainfall deficits, yield shocks, and input cost escalations.
    """
    @staticmethod
    def run_simulation(req: SimulationRequest) -> SimulationResponse:
        area = Decimal(str(req.area_acres))
        base_yield_acre = Decimal(str(req.baseline_yield_quintals_per_acre))
        base_price = Decimal(str(req.baseline_market_price_per_quintal))
        base_cost = Decimal(str(req.baseline_cultivation_cost))

        # Baseline Calculations
        base_total_yield = (area * base_yield_acre).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        base_gross_revenue = (base_total_yield * base_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        base_net_profit = (base_gross_revenue - base_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        baseline_result = ScenarioResult(
            scenario_name="Baseline Plan",
            price_per_quintal=base_price,
            total_yield_quintals=base_total_yield,
            cultivation_cost=base_cost,
            gross_revenue=base_gross_revenue,
            net_profit=base_net_profit,
            profit_difference=Decimal("0.00"),
            percentage_profit_impact=Decimal("0.00"),
        )

        # Apply shifts
        # Price shift
        price_factor = (Decimal("1") + (Decimal(str(req.price_change_percent)) / Decimal("100")))
        sim_price = (base_price * price_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Yield shift (affected by direct yield % change or rainfall deficit correlation)
        yield_shift = Decimal(str(req.yield_change_percent))
        if req.rainfall_change_percent < Decimal("0"):
            # e.g., -25% rainfall without adequate irrigation could reduce yield by approx 0.4x rainfall deficit
            rain_yield_penalty = (Decimal(str(req.rainfall_change_percent)) * Decimal("0.4"))
            yield_shift = yield_shift + rain_yield_penalty

        yield_factor = (Decimal("1") + (yield_shift / Decimal("100")))
        sim_total_yield = (base_total_yield * yield_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Cost shift
        cost_factor = (Decimal("1") + (Decimal(str(req.cost_change_percent)) / Decimal("100")))
        sim_cost = (base_cost * cost_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Scenario Results
        sim_revenue = (sim_total_yield * sim_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sim_profit = (sim_revenue - sim_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        profit_diff = (sim_profit - base_net_profit).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        pct_impact = Decimal("0.00")
        if base_net_profit != Decimal("0"):
            pct_impact = ((profit_diff / abs(base_net_profit)) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        sim_result = ScenarioResult(
            scenario_name="Simulated Scenario",
            price_per_quintal=sim_price,
            total_yield_quintals=sim_total_yield,
            cultivation_cost=sim_cost,
            gross_revenue=sim_revenue,
            net_profit=sim_profit,
            profit_difference=profit_diff,
            percentage_profit_impact=pct_impact,
        )

        # Risk / impact explanation
        explanation = (
            f"Under this simulation, your net profit changes from ₹{base_net_profit:,.2f} to ₹{sim_profit:,.2f} "
            f"({profit_diff:+,.2f} INR, {pct_impact:+.1f}% impact). "
        )
        if profit_diff < Decimal("0"):
            explanation += "The primary risk drivers are market price deflation and potential yield volatility."
        else:
            explanation += "Favorable market prices or yield optimization significantly increase surplus margin."

        hedging_actions: List[str] = []
        if req.price_change_percent < Decimal("0"):
            hedging_actions.append("Consider phased selling across local and cold storage instead of immediate distress sale.")
            hedging_actions.append("Check transport arbitrage to Guntur / Warangal benchmark mandis for higher modal rates.")
        if req.rainfall_change_percent < Decimal("0"):
            hedging_actions.append("Switch to micro-irrigation / drip scheduling in early morning hours to conserve root moisture.")
            hedging_actions.append("Apply mulching to minimize soil evaporation.")

        return SimulationResponse(
            crop_name=req.crop_name,
            baseline=baseline_result,
            simulated_scenario=sim_result,
            risk_impact_explanation=explanation,
            recommended_hedging_actions=hedging_actions,
        )

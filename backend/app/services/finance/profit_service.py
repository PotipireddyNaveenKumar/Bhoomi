from decimal import Decimal, ROUND_HALF_UP
from app.schemas.finance import ProfitCalculationRequest, ProfitCalculationResponse

class FinancialService:
    """
    Deterministic Financial Intelligence Engine for agricultural profit, revenue,
    and cost computations using exact Decimal arithmetic.
    
    Rule: Never allow LLMs to invent numerical financial calculations.
    """
    @staticmethod
    def calculate_profit(req: ProfitCalculationRequest) -> ProfitCalculationResponse:
        area = Decimal(str(req.area_acres))
        yield_per_acre = Decimal(str(req.expected_yield_quintals_per_acre))
        price_per_quintal = Decimal(str(req.expected_market_price_per_quintal))
        total_cost = Decimal(str(req.cultivation_cost_total))

        # Gross Revenue = Total Production (Quintals) * Market Price
        # Total Production = Area * Yield/Acre
        total_production = (area * yield_per_acre).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        gross_revenue = (total_production * price_per_quintal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Net Profit = Gross Revenue - Total Cultivation Cost
        net_profit = (gross_revenue - total_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Profit per Acre
        profit_per_acre = (net_profit / area if area > Decimal("0") else Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # ROI % = (Net Profit / Total Cost) * 100
        roi = ((net_profit / total_cost) * Decimal("100") if total_cost > Decimal("0") else Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        explanation = (
            f"For {area} acres of {req.crop_name} producing {total_production} quintals "
            f"sold at ₹{price_per_quintal:,.2f}/quintal, Gross Revenue is ₹{gross_revenue:,.2f}. "
            f"After deducting cultivation costs of ₹{total_cost:,.2f}, Net Profit is ₹{net_profit:,.2f} "
            f"(₹{profit_per_acre:,.2f}/acre, ROI: {roi}%)."
        )

        return ProfitCalculationResponse(
            crop_name=req.crop_name,
            area_acres=area,
            total_production_quintals=total_production,
            market_price_per_quintal=price_per_quintal,
            gross_revenue=gross_revenue,
            cultivation_cost_total=total_cost,
            net_profit=net_profit,
            profit_per_acre=profit_per_acre,
            return_on_investment_percent=roi,
            explanation=explanation,
        )

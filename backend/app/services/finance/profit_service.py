from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional
from app.schemas.finance import ProfitCalculationRequest, ProfitCalculationResponse

class FinancialService:
    """
    Deterministic Financial Intelligence Engine for agricultural profit, revenue,
    cost, and break-even computations using exact Decimal arithmetic.
    
    Rule: Never allow LLMs to invent numerical financial calculations.
    """
    @staticmethod
    def calculate_profit(req: ProfitCalculationRequest) -> ProfitCalculationResponse:
        calculation_trace: List[str] = []
        warnings: List[str] = []
        assumptions: List[str] = []

        # 1. Extract and validate land area
        raw_area = req.land_area if req.land_area is not None else req.area_acres
        if raw_area is None:
            raw_area = Decimal("1.0")
            assumptions.append("Land area not provided; assumed default of 1.0 unit.")
        
        area = Decimal(str(raw_area))
        if area <= Decimal("0"):
            raise ValueError("Land area must be greater than zero.")

        area_unit = req.area_unit.lower().strip() if req.area_unit else "acre"
        if area_unit not in ("acre", "acres", "hectare", "hectares", "ha"):
            raise ValueError(f"Unsupported area unit: {area_unit}. Supported: 'acre', 'hectare'.")

        is_hectare = area_unit in ("hectare", "hectares", "ha")
        if is_hectare:
            area_acres = (area * Decimal("2.47105")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            assumptions.append(f"Converted {area} hectare(s) to {area_acres} acres (1 ha = 2.47105 acres).")
        else:
            area_acres = area

        calculation_trace.append(f"Input Land Area: {area} {area_unit} ({area_acres} acres)")

        # 2. 7-Component Cultivation Cost Summation
        cost_components: Dict[str, Optional[Decimal]] = {
            "seed_cost": Decimal(str(req.seed_cost)) if req.seed_cost is not None else None,
            "fertilizer_cost": Decimal(str(req.fertilizer_cost)) if req.fertilizer_cost is not None else None,
            "pesticide_cost": Decimal(str(req.pesticide_cost)) if req.pesticide_cost is not None else None,
            "labour_cost": Decimal(str(req.labour_cost)) if req.labour_cost is not None else None,
            "irrigation_cost": Decimal(str(req.irrigation_cost)) if req.irrigation_cost is not None else None,
            "machinery_cost": Decimal(str(req.machinery_cost)) if req.machinery_cost is not None else None,
            "other_cost": Decimal(str(req.other_cost)) if req.other_cost is not None else None,
        }

        # Check for negative cost inputs
        for c_name, c_val in cost_components.items():
            if c_val is not None and c_val < Decimal("0"):
                raise ValueError(f"{c_name} cannot be negative ({c_val}).")

        # Sum individual cost components if any are provided
        active_components = {k: v for k, v in cost_components.items() if v is not None}
        if active_components:
            total_cost = sum(active_components.values(), Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            breakdown_trace = " + ".join([f"₹{v:,.2f} ({k})" for k, v in active_components.items()])
            calculation_trace.append(f"Cultivation Cost Breakdown: {breakdown_trace}")
            calculation_trace.append(f"Total Cultivation Cost = {breakdown_trace} = ₹{total_cost:,.2f}")
        elif req.cultivation_cost_total is not None:
            total_cost = Decimal(str(req.cultivation_cost_total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if total_cost < Decimal("0"):
                raise ValueError(f"cultivation_cost_total cannot be negative ({total_cost}).")
            active_components["cultivation_cost_total"] = total_cost
            calculation_trace.append(f"Cultivation Cost Breakdown: Lump sum cultivation cost ₹{total_cost:,.2f}")
            calculation_trace.append(f"Total Cultivation Cost (lump sum) = ₹{total_cost:,.2f}")
        else:
            total_cost = Decimal("0.00")
            warnings.append("No cultivation costs provided; total cost assumed as ₹0.00.")
            calculation_trace.append("Total Cultivation Cost = ₹0.00")

        # Create expanded cost breakdown containing both 'seed' and 'seed_cost'
        expanded_breakdown = dict(active_components)
        for k, v in list(active_components.items()):
            if k.endswith("_cost"):
                expanded_breakdown[k[:-5]] = v

        # 3. Extract and validate Expected Yield
        raw_yield = req.expected_yield if req.expected_yield is not None else req.expected_yield_quintals_per_acre
        raw_price = req.expected_market_price if req.expected_market_price is not None else req.expected_market_price_per_quintal

        missing_fields: List[str] = []
        if raw_yield is None:
            missing_fields.append("expected_yield")
        if raw_price is None:
            missing_fields.append("expected_market_price")

        # Compute partial break-even metrics if one of the values is present
        break_even_price = None
        break_even_yield = None
        if raw_yield is not None and total_cost > Decimal("0"):
            y_temp = Decimal(str(raw_yield))
            y_u = req.yield_unit.lower().strip() if req.yield_unit else "quintal"
            if y_u in ("kg", "kilogram", "kilograms"):
                ypa_qtl = (y_temp / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif y_u in ("tonne", "tonnes", "ton", "tons", "t"):
                ypa_qtl = (y_temp * Decimal("10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                ypa_qtl = y_temp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            p_qtl = (area_acres * ypa_qtl).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if p_qtl > Decimal("0"):
                break_even_price = (total_cost / p_qtl).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                calculation_trace.append(f"Break-Even Price = ₹{total_cost:,.2f} ÷ {p_qtl} q = ₹{break_even_price:,.2f}/quintal")

        if raw_price is not None and total_cost > Decimal("0"):
            p_temp = Decimal(str(raw_price))
            pr_u = req.price_unit.lower().strip() if req.price_unit else "rupees_per_quintal"
            if pr_u in ("rupees_per_kg", "rs_per_kg", "inr_per_kg", "per_kg"):
                pr_qtl = (p_temp * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                pr_qtl = p_temp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if pr_qtl > Decimal("0"):
                needed_prod = (total_cost / pr_qtl).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                break_even_yield = (needed_prod / area_acres).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                calculation_trace.append(f"Break-Even Yield = ₹{total_cost:,.2f} ÷ ₹{pr_qtl:,.2f}/q ÷ {area_acres} acres = {break_even_yield} q/acre")

        # 4. Handle Partial Calculation (Missing Yield or Price) - Never hallucinate missing values
        if missing_fields:
            warnings.append(
                f"Missing required financial inputs: {', '.join(missing_fields)}. "
                f"Gross revenue, net profit, and complete ROI cannot be determined without inventing values."
            )
            explanation = (
                f"Partial Financial Calculation for {area} {area_unit} of {req.crop_name}: "
                f"Total Cultivation Cost is ₹{total_cost:,.2f}. "
                + (f"Break-Even Market Price is ₹{break_even_price:,.2f}/quintal. " if break_even_price else "")
                + (f"Break-Even Yield is {break_even_yield} q/{area_unit}. " if break_even_yield else "")
                + f"Please provide {', '.join(missing_fields)} to calculate expected gross revenue and net profit."
            )
            return ProfitCalculationResponse(
                crop_name=req.crop_name,
                land_area=area,
                area_unit=area_unit,
                area_acres=area_acres,
                total_cost=total_cost,
                cultivation_cost_total=total_cost,
                cost_breakdown=expanded_breakdown,
                total_production_quintals=None,
                market_price_per_quintal=None,
                gross_revenue=None,
                net_profit=None,
                profit_per_area=None,
                profit_per_acre=None,
                break_even_price=break_even_price,
                break_even_yield=break_even_yield,
                return_on_investment_percent=None,
                is_partial=True,
                missing_fields=missing_fields,
                calculation_trace=calculation_trace,
                warnings=warnings,
                assumptions=assumptions,
                currency="INR (₹)",
                explanation=explanation,
            )

        # 5. Full Calculation - Normalize Yield and Price Units
        y_val = Decimal(str(raw_yield))
        p_val = Decimal(str(raw_price))
        if y_val < Decimal("0"):
            raise ValueError(f"expected_yield cannot be negative ({y_val}).")
        if p_val < Decimal("0"):
            raise ValueError(f"expected_market_price cannot be negative ({p_val}).")

        # Normalize yield to Quintals per area unit
        y_unit = req.yield_unit.lower().strip() if req.yield_unit else "quintal"
        if y_unit in ("kg", "kilogram", "kilograms"):
            yield_per_acre_qtl = (y_val / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            assumptions.append(f"Converted yield from {y_val} kg to {yield_per_acre_qtl} quintals (100 kg = 1 quintal).")
        elif y_unit in ("tonne", "tonnes", "ton", "tons", "t"):
            yield_per_acre_qtl = (y_val * Decimal("10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            assumptions.append(f"Converted yield from {y_val} tonnes to {yield_per_acre_qtl} quintals (1 tonne = 10 quintals).")
        else:
            yield_per_acre_qtl = y_val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total_production_qtl = (area_acres * yield_per_acre_qtl).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        calculation_trace.append(f"Total Production = {area_acres} acres × {yield_per_acre_qtl} q/acre = {total_production_qtl} quintals")

        # Normalize price to ₹/Quintal
        p_unit = req.price_unit.lower().strip() if req.price_unit else "rupees_per_quintal"
        if p_unit in ("rupees_per_kg", "rs_per_kg", "inr_per_kg", "per_kg"):
            price_per_qtl = (p_val * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            assumptions.append(f"Converted price from ₹{p_val}/kg to ₹{price_per_qtl}/quintal (₹/kg × 100).")
        else:
            price_per_qtl = p_val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        calculation_trace.append(f"Effective Market Price = ₹{price_per_qtl:,.2f}/quintal")

        # 6. Authoritative Deterministic Arithmetic
        # Gross Revenue = Total Production (q) × Price per quintal
        gross_revenue = (total_production_qtl * price_per_qtl).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        calculation_trace.append(f"Gross Revenue = {total_production_qtl} q × ₹{price_per_qtl:,.2f}/q = ₹{gross_revenue:,.2f}")

        # Net Profit = Gross Revenue − Total Cultivation Cost
        net_profit = (gross_revenue - total_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        calculation_trace.append(f"Net Profit = ₹{gross_revenue:,.2f} − ₹{total_cost:,.2f} = ₹{net_profit:,.2f}")

        # Profit per Area Unit
        profit_per_area = (net_profit / area).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if area > Decimal("0") else Decimal("0.00")
        profit_per_acre = (net_profit / area_acres).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if area_acres > Decimal("0") else Decimal("0.00")
        calculation_trace.append(f"Profit per {area_unit} = ₹{net_profit:,.2f} ÷ {area} {area_unit} = ₹{profit_per_area:,.2f}/{area_unit}")

        # Break-Even Price = Total Cost ÷ Total Production
        if total_production_qtl > Decimal("0"):
            break_even_price = (total_cost / total_production_qtl).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            calculation_trace.append(f"Break-Even Price = ₹{total_cost:,.2f} ÷ {total_production_qtl} q = ₹{break_even_price:,.2f}/quintal")
        else:
            break_even_price = None
            warnings.append("Expected yield is 0; break-even price cannot be computed (division by zero).")

        # Break-Even Yield = Total Cost ÷ Price per Quintal
        if price_per_qtl > Decimal("0"):
            break_even_yield = (total_cost / price_per_qtl).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            calculation_trace.append(f"Break-Even Yield = ₹{total_cost:,.2f} ÷ ₹{price_per_qtl:,.2f}/q = {break_even_yield} quintals")
        else:
            break_even_yield = None
            warnings.append("Expected market price is 0; break-even yield cannot be computed (division by zero).")

        # Return on Investment %
        if total_cost > Decimal("0"):
            roi = ((net_profit / total_cost) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            calculation_trace.append(f"Return on Investment (ROI) = (₹{net_profit:,.2f} ÷ ₹{total_cost:,.2f}) × 100 = {roi}%")
        else:
            roi = Decimal("0.00")

        explanation = (
            f"For {area} {area_unit} of {req.crop_name} yielding {total_production_qtl} quintals "
            f"sold at ₹{price_per_qtl:,.2f}/quintal: Gross Revenue is ₹{gross_revenue:,.2f}. "
            f"After total cultivation costs of ₹{total_cost:,.2f}, estimated Net Profit is ₹{net_profit:,.2f} "
            f"(₹{profit_per_area:,.2f}/{area_unit}, ROI: {roi}%). "
            f"Break-even threshold: Price ≥ ₹{break_even_price:,.2f}/q or Yield ≥ {break_even_yield} q."
            if break_even_price and break_even_yield else
            f"For {area} {area_unit} of {req.crop_name}: Gross Revenue is ₹{gross_revenue:,.2f}, "
            f"Net Profit is ₹{net_profit:,.2f} against Total Cost of ₹{total_cost:,.2f}."
        )

        return ProfitCalculationResponse(
            crop_name=req.crop_name,
            land_area=area,
            area_unit=area_unit,
            area_acres=area_acres,
            total_cost=total_cost,
            cultivation_cost_total=total_cost,
            cost_breakdown=expanded_breakdown,
            total_production_quintals=total_production_qtl,
            market_price_per_quintal=price_per_qtl,
            gross_revenue=gross_revenue,
            net_profit=net_profit,
            profit_per_area=profit_per_area,
            profit_per_acre=profit_per_acre,
            break_even_price=break_even_price,
            break_even_yield=break_even_yield,
            return_on_investment_percent=roi,
            is_partial=False,
            missing_fields=[],
            calculation_trace=calculation_trace,
            warnings=warnings,
            assumptions=assumptions,
            currency="INR (₹)",
            explanation=explanation,
        )

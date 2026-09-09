from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class ContingencyPlan(BaseModel):
    trigger_condition: str
    scenario_description: str
    adaptation_actions: List[str]
    financial_impact_estimate: str
    risk_mitigation: str

class FarmPlan(BaseModel):
    plan_id: str
    farmer_id: str
    farm_id: str
    crop_name: str
    area_acres: float
    target_yield_quintals: float
    current_stage: str
    sowing_date: str
    estimated_harvest_window: str
    irrigation_schedule: str
    nutrient_management_plan: str
    crop_health_scouting_protocol: str
    market_dispatch_strategy: str
    financial_budget: Dict[str, float]
    contingency_plans: List[ContingencyPlan]
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class FarmPlanManager:
    """
    Adaptive Farm Plan Manager.
    Maintains the farmer's operational blueprint and dynamically updates tasks
    and contingencies whenever weather, market, or crop health deviates from baseline.
    """
    _plans: Dict[str, FarmPlan] = {}

    @classmethod
    def create_or_update_plan(
        cls,
        farmer_id: str,
        farm_id: str,
        crop_name: str = "Chilli",
        area_acres: float = 3.0,
        sowing_date: str = "2026-07-15"
    ) -> FarmPlan:
        contingencies = [
            ContingencyPlan(
                trigger_condition="Rainfall Deficit (>25% below normal)",
                scenario_description="Mid-season dry spell during fruit enlargement",
                adaptation_actions=[
                    "Switch from furrow flood irrigation to alternate furrow or drip intervals",
                    "Apply foliar spray of Potassium Silicate (2ml/L) or Anti-transpirant to preserve leaf turgor",
                    "Mulch rows with organic paddy straw to reduce soil evaporation"
                ],
                financial_impact_estimate="Preserves 85-90% of expected yield; saves ₹8,000 in emergency water tanker costs.",
                risk_mitigation="Reduces drought shock risk from HIGH to LOW."
            ),
            ContingencyPlan(
                trigger_condition="Market Spot Price Crash (>15% fall below ₹11,000/Q)",
                scenario_description="Heavy regional arrival glut at Guntur APMC",
                adaptation_actions=[
                    "Deposit dried pods into Guntur cold storage facilities (~₹35/bag/month)",
                    "Compare Khammam and Warangal APMC spot rates for transport arbitrage",
                    "Negotiate direct farm-gate sales with certified spice exporters"
                ],
                financial_impact_estimate="Protects against ₹30,000 - ₹50,000 distress liquidation loss.",
                risk_mitigation="Eliminates distress selling pressure."
            )
        ]

        plan = FarmPlan(
            plan_id=f"plan_{farmer_id}_{crop_name.lower()}",
            farmer_id=farmer_id,
            farm_id=farm_id,
            crop_name=crop_name,
            area_acres=area_acres,
            target_yield_quintals=round(area_acres * 10.0, 1),
            current_stage="flowering",
            sowing_date=sowing_date,
            estimated_harvest_window="December 5 - December 20, 2026",
            irrigation_schedule="Furrow irrigation every 5-6 days; hold if rain >= 40%",
            nutrient_management_plan="Basal FYM + SSP + MOP; 19:19:19 + Boron foliar spray during flowering",
            crop_health_scouting_protocol="Twice-weekly scouting for thrips and mites on lower leaf canopy",
            market_dispatch_strategy=f"Target Guntur APMC spot realization >= ₹12,000/Q; cold storage fallback",
            financial_budget={
                "estimated_gross_revenue": round(area_acres * 10.0 * 12200.0, 2),
                "estimated_cultivation_cost": 70000.0,
                "projected_net_profit": round((area_acres * 10.0 * 12200.0) - 70000.0, 2)
            },
            contingency_plans=contingencies
        )

        cls._plans[farmer_id] = plan
        return plan

    @classmethod
    def get_plan(cls, farmer_id: str) -> Optional[FarmPlan]:
        return cls._plans.get(farmer_id)

from decimal import Decimal
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class SimulationRequest(BaseModel):
    crop_name: str = Field(..., example="Chilli")
    area_acres: Decimal = Field(..., example=3.0)
    baseline_yield_quintals_per_acre: Decimal = Field(..., example=10.0)
    baseline_market_price_per_quintal: Decimal = Field(..., example=12000.0)
    baseline_cultivation_cost: Decimal = Field(..., example=70000.0)
    # Scenario percentage shifts (e.g. -20 for -20%, +10 for +10%)
    price_change_percent: Decimal = Field(default=Decimal("0.0"), example=-20.0)
    yield_change_percent: Decimal = Field(default=Decimal("0.0"), example=0.0)
    cost_change_percent: Decimal = Field(default=Decimal("0.0"), example=0.0)
    rainfall_change_percent: Decimal = Field(default=Decimal("0.0"), example=-25.0)

class ScenarioResult(BaseModel):
    scenario_name: str
    price_per_quintal: Decimal
    total_yield_quintals: Decimal
    cultivation_cost: Decimal
    gross_revenue: Decimal
    net_profit: Decimal
    profit_difference: Decimal
    percentage_profit_impact: Decimal

class SimulationResponse(BaseModel):
    crop_name: str
    baseline: ScenarioResult
    simulated_scenario: ScenarioResult
    risk_impact_explanation: str
    recommended_hedging_actions: List[str]

from decimal import Decimal
from typing import Optional, Dict
from pydantic import BaseModel, Field

class ProfitCalculationRequest(BaseModel):
    crop_name: str = Field(..., example="Chilli")
    area_acres: Decimal = Field(..., example=3.0)
    expected_yield_quintals_per_acre: Decimal = Field(..., example=10.0)
    expected_market_price_per_quintal: Decimal = Field(..., example=12000.0)
    cultivation_cost_total: Decimal = Field(..., example=70000.0)

class ProfitCalculationResponse(BaseModel):
    crop_name: str
    area_acres: Decimal
    total_production_quintals: Decimal
    market_price_per_quintal: Decimal
    gross_revenue: Decimal
    cultivation_cost_total: Decimal
    net_profit: Decimal
    profit_per_acre: Decimal
    return_on_investment_percent: Decimal
    currency: str = "INR (₹)"
    explanation: str

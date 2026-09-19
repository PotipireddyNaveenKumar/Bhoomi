from decimal import Decimal
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

class ProfitCalculationRequest(BaseModel):
    crop_name: str = Field(..., example="Chilli")
    land_area: Optional[Decimal] = Field(default=None, example=3.0)
    area_acres: Optional[Decimal] = Field(default=None, example=3.0)
    area_unit: str = Field(default="acre", example="acre")  # "acre", "hectare"
    
    # 7-component cultivation cost breakdown
    seed_cost: Optional[Decimal] = Field(default=None, example=5000.0)
    fertilizer_cost: Optional[Decimal] = Field(default=None, example=12000.0)
    pesticide_cost: Optional[Decimal] = Field(default=None, example=8000.0)
    labour_cost: Optional[Decimal] = Field(default=None, example=25000.0)
    irrigation_cost: Optional[Decimal] = Field(default=None, example=6000.0)
    machinery_cost: Optional[Decimal] = Field(default=None, example=10000.0)
    other_cost: Optional[Decimal] = Field(default=None, example=4000.0)
    cultivation_cost_total: Optional[Decimal] = Field(default=None, example=70000.0)

    # Yield & Price parameters
    expected_yield: Optional[Decimal] = Field(default=None, example=10.0)
    expected_yield_quintals_per_acre: Optional[Decimal] = Field(default=None, example=10.0)
    yield_unit: str = Field(default="quintal", example="quintal")  # "quintal", "kg", "tonne"
    
    expected_market_price: Optional[Decimal] = Field(default=None, example=12000.0)
    expected_market_price_per_quintal: Optional[Decimal] = Field(default=None, example=12000.0)
    price_unit: str = Field(default="rupees_per_quintal", example="rupees_per_quintal")  # "rupees_per_quintal", "rupees_per_kg"
    
    revenue_assumptions: Optional[str] = None

class ProfitCalculationResponse(BaseModel):
    crop_name: str
    land_area: Decimal
    area_unit: str = "acre"
    area_acres: Decimal
    total_cost: Decimal
    cultivation_cost_total: Decimal
    cost_breakdown: Dict[str, Decimal] = Field(default_factory=dict)
    total_production_quintals: Optional[Decimal] = None
    market_price_per_quintal: Optional[Decimal] = None
    gross_revenue: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    profit_per_area: Optional[Decimal] = None
    profit_per_acre: Optional[Decimal] = None
    break_even_price: Optional[Decimal] = None
    break_even_yield: Optional[Decimal] = None
    return_on_investment_percent: Optional[Decimal] = None
    is_partial: bool = False
    missing_fields: List[str] = Field(default_factory=list)
    calculation_trace: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    currency: str = "INR (₹)"
    explanation: str


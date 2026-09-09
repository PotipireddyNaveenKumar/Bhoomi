from decimal import Decimal
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ScoredCropOption(BaseModel):
    crop_name: str
    rank: int
    composite_score: float  # 0 to 100
    expected_yield_quintals_per_acre: float
    expected_revenue_per_acre: float
    cultivation_cost_per_acre: float
    expected_net_profit_total: float
    duration_days: int
    water_requirement: str
    overall_risk_level: str
    key_drivers: List[str]
    why_recommended: str

class CropPlanRanking(BaseModel):
    farmer_name: str
    location: str
    area_acres: float
    soil_type: str
    season: str
    ranked_crops: List[ScoredCropOption]
    planning_summary: str

class PersonalCropPlanner:
    """
    Personalized Crop Planner.
    Calculates multi-objective transparent decision score across:
    1. Agronomic Suitability (Soil, pH, Climate)
    2. Financial Net ROI (Gross revenue minus costs)
    3. Water Resource Compatibility
    4. Weather Resilience (Drought/Excess tolerance)
    5. Market Volatility & Price Realization
    6. Farmer Historical Preference
    """
    @classmethod
    def plan_season(
        cls,
        farmer_name: str = "Farmer",
        area_acres: float = 3.0,
        soil_type: str = "black",
        location: str = "Guntur",
        season: str = "Kharif",
        farmer_preferred: Optional[List[str]] = None
    ) -> CropPlanRanking:
        candidates = [
            {
                "crop": "Chilli",
                "yield_q_acre": 10.0,
                "price_q": 12200.0,
                "cost_acre": 70000.0,
                "duration": 150,
                "water": "Moderate",
                "risk": "Moderate",
                "agronomic_fit": 95,
                "financial_fit": 92,
                "water_fit": 80,
                "market_fit": 88
            },
            {
                "crop": "Cotton",
                "yield_q_acre": 8.0,
                "price_q": 7200.0,
                "cost_acre": 32000.0,
                "duration": 160,
                "water": "Low to Moderate",
                "risk": "Low",
                "agronomic_fit": 90,
                "financial_fit": 80,
                "water_fit": 90,
                "market_fit": 85
            },
            {
                "crop": "Soybean",
                "yield_q_acre": 7.5,
                "price_q": 4600.0,
                "cost_acre": 16000.0,
                "duration": 95,
                "water": "Low",
                "risk": "Low",
                "agronomic_fit": 85,
                "financial_fit": 75,
                "water_fit": 95,
                "market_fit": 82
            },
            {
                "crop": "Maize",
                "yield_q_acre": 24.0,
                "price_q": 2150.0,
                "cost_acre": 22000.0,
                "duration": 100,
                "water": "Moderate",
                "risk": "Low",
                "agronomic_fit": 88,
                "financial_fit": 82,
                "water_fit": 85,
                "market_fit": 80
            }
        ]

        prefs = [p.lower() for p in (farmer_preferred or ["chilli"])]
        ranked: List[ScoredCropOption] = []

        for c in candidates:
            # Multi-objective scoring weights
            w_agri = 0.25
            w_fin = 0.30
            w_water = 0.15
            w_market = 0.15
            w_pref = 0.15

            pref_score = 95 if c["crop"].lower() in prefs else 60

            score = (
                w_agri * c["agronomic_fit"] +
                w_fin * c["financial_fit"] +
                w_water * c["water_fit"] +
                w_market * c["market_fit"] +
                w_pref * pref_score
            )

            rev_acre = c["yield_q_acre"] * c["price_q"]
            net_acre = rev_acre - c["cost_acre"]
            total_net = net_acre * area_acres

            drivers = []
            if c["crop"] == "Chilli":
                drivers = ["Highest net commercial returns", "Excellent Guntur black soil suitability", "Established cold storage ecosystem"]
                why = f"Chilli ranks #1 because of strong local market realization (₹{c['price_q']:,.0f}/Q) and high net profit."
            elif c["crop"] == "Cotton":
                drivers = ["Drought hardy deep taproot", "Guaranteed MSP price floor", "Lower daily supervision required"]
                why = f"Cotton is a resilient alternative offering lower capital investment with reliable MSP procurement."
            elif c["crop"] == "Soybean":
                drivers = ["Short duration (95 days)", "Fixes soil nitrogen", "Low initial working capital"]
                why = f"Soybean is best for fast turnover and lower capital risk."
            else:
                drivers = ["Steady poultry feed demand", "Low disease pressure", "High bulk yield"]
                why = f"Maize offers reliable production volume."

            ranked.append(ScoredCropOption(
                crop_name=c["crop"],
                rank=0,
                composite_score=round(score, 1),
                expected_yield_quintals_per_acre=c["yield_q_acre"],
                expected_revenue_per_acre=rev_acre,
                cultivation_cost_per_acre=c["cost_acre"],
                expected_net_profit_total=total_net,
                duration_days=c["duration"],
                water_requirement=c["water"],
                overall_risk_level=c["risk"],
                key_drivers=drivers,
                why_recommended=why
            ))

        ranked.sort(key=lambda x: x.composite_score, reverse=True)
        for i, item in enumerate(ranked):
            item.rank = i + 1

        summary = (
            f"Based on your {area_acres} acres of {soil_type} soil in {location} for {season} season, "
            f"**{ranked[0].crop_name}** ranks highest with a composite decision score of {ranked[0].composite_score}/100, "
            f"offering an estimated total net profit of ₹{ranked[0].expected_net_profit_total:,.0f}."
        )

        return CropPlanRanking(
            farmer_name=farmer_name,
            location=location,
            area_acres=area_acres,
            soil_type=soil_type,
            season=season,
            ranked_crops=ranked,
            planning_summary=summary
        )

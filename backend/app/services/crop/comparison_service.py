from decimal import Decimal
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.finance.profit_service import FinancialService
from app.schemas.finance import ProfitCalculationRequest

class CropComparisonItem(BaseModel):
    crop_name: str
    duration_days: int
    water_requirement: str  # Low, Moderate, High
    expected_yield_quintals_per_acre: Decimal
    market_price_per_quintal: Decimal
    gross_revenue_per_acre: Decimal
    cultivation_cost_per_acre: Decimal
    net_profit_per_acre: Decimal
    net_profit_total: Decimal
    disease_risk: str
    market_volatility: str
    key_advantages: List[str]
    cautions: List[str]

class CropComparisonResponse(BaseModel):
    area_acres: Decimal
    soil_type: str
    location: str
    recommended_crop: str
    comparison: List[CropComparisonItem]
    decision_rationale: str

class CropComparisonService:
    # Agronomic baselines for major Indian crops
    CROP_BENCHMARKS = {
        "chilli": {
            "duration": 150,
            "water": "Moderate to High",
            "yield_per_acre": Decimal("10.0"),
            "price_per_quintal": Decimal("12000.00"),
            "cost_per_acre": Decimal("70000.00"),
            "disease_risk": "Moderate (Thrips, Leaf Curl)",
            "market_volatility": "Moderate",
            "advantages": ["High commercial gross returns", "Established Guntur APMC market demand", "Cold storage option available"],
            "cautions": ["Requires intensive pest scouting", "Higher upfront capital expenditure"]
        },
        "cotton": {
            "duration": 160,
            "water": "Moderate",
            "yield_per_acre": Decimal("8.0"),
            "price_per_quintal": Decimal("7200.00"),
            "cost_per_acre": Decimal("32000.00"),
            "disease_risk": "Moderate (Pink Bollworm, Whitefly)",
            "market_volatility": "Low (MSP support available)",
            "advantages": ["Government MSP safety net", "Deep taproot drought tolerance", "Lower daily supervision than vegetables"],
            "cautions": ["Susceptible to late-season pink bollworm", "Cotton price cycles"]
        },
        "rice": {
            "duration": 120,
            "water": "High (Standing Water)",
            "yield_per_acre": Decimal("22.0"),
            "price_per_quintal": Decimal("2300.00"),
            "cost_per_acre": Decimal("26000.00"),
            "disease_risk": "Low to Moderate (Blast, BLB)",
            "market_volatility": "Low (Government Procurement)",
            "advantages": ["Stable procurement centers", "Low price volatility", "Familiar cultural practices"],
            "cautions": ["High water dependency", "High fertilizer and weed management needs"]
        },
        "maize": {
            "duration": 100,
            "water": "Low to Moderate",
            "yield_per_acre": Decimal("24.0"),
            "price_per_quintal": Decimal("2150.00"),
            "cost_per_acre": Decimal("22000.00"),
            "disease_risk": "Low (Fall Armyworm alert)",
            "market_volatility": "Low to Moderate",
            "advantages": ["Short crop duration (100 days)", "High poultry feed market demand", "Good crop rotation choice"],
            "cautions": ["Scout for Fall Armyworm during whorl stage"]
        },
        "soybean": {
            "duration": 95,
            "water": "Low",
            "yield_per_acre": Decimal("7.5"),
            "price_per_quintal": Decimal("4600.00"),
            "cost_per_acre": Decimal("16000.00"),
            "disease_risk": "Low (Yellow Mosaic Virus)",
            "market_volatility": "Moderate",
            "advantages": ["Short duration", "Fixes atmospheric nitrogen, improving soil fertility", "Low initial investment"],
            "cautions": ["Sensitive to moisture stress at flowering and pod filling"]
        },
        "pigeonpea": {
            "duration": 170,
            "water": "Low (Drought Hardy)",
            "yield_per_acre": Decimal("6.0"),
            "price_per_quintal": Decimal("7500.00"),
            "cost_per_acre": Decimal("18000.00"),
            "disease_risk": "Low to Moderate (Sterility Mosaic, Pod Borer)",
            "market_volatility": "Low (High domestic pulse demand)",
            "advantages": ["Excellent drought tolerance", "Deep taproot breaks soil plow layer", "Premium pulse market price"],
            "cautions": ["Longer crop duration (5-6 months)"]
        }
    }

    @classmethod
    def compare_crops(
        cls,
        crop_names: List[str],
        area_acres: Decimal = Decimal("3.0"),
        soil_type: str = "black",
        location: str = "Guntur"
    ) -> CropComparisonResponse:
        items: List[CropComparisonItem] = []

        for name in crop_names:
            key = name.strip().lower()
            data = cls.CROP_BENCHMARKS.get(key)
            if not data:
                # General default estimate
                data = {
                    "duration": 120,
                    "water": "Moderate",
                    "yield_per_acre": Decimal("10.0"),
                    "price_per_quintal": Decimal("4000.00"),
                    "cost_per_acre": Decimal("25000.00"),
                    "disease_risk": "Moderate",
                    "market_volatility": "Moderate",
                    "advantages": ["Standard regional market demand"],
                    "cautions": ["Verify local mandi arrival rates"]
                }

            # Exact Financial Calculations
            gross_per_acre = data["yield_per_acre"] * data["price_per_quintal"]
            net_per_acre = gross_per_acre - data["cost_per_acre"]
            net_total = net_per_acre * area_acres

            items.append(CropComparisonItem(
                crop_name=name.title(),
                duration_days=data["duration"],
                water_requirement=data["water"],
                expected_yield_quintals_per_acre=data["yield_per_acre"],
                market_price_per_quintal=data["price_per_quintal"],
                gross_revenue_per_acre=gross_per_acre,
                cultivation_cost_per_acre=data["cost_per_acre"],
                net_profit_per_acre=net_per_acre,
                net_profit_total=net_total,
                disease_risk=data["disease_risk"],
                market_volatility=data["market_volatility"],
                key_advantages=data["advantages"],
                cautions=data["cautions"]
            ))

        # Best profit option
        best_crop = max(items, key=lambda x: x.net_profit_total)

        rationale = (
            f"Comparing {', '.join([i.crop_name for i in items])} for {area_acres} acres of {soil_type} soil: "
            f"**{best_crop.crop_name}** offers the highest projected Net Profit of ₹{best_crop.net_profit_total:,.0f} "
            f"(₹{best_crop.net_profit_per_acre:,.0f}/acre), factoring in expected yield ({best_crop.expected_yield_quintals_per_acre} q/acre) "
            f"and current market realization."
        )

        return CropComparisonResponse(
            area_acres=area_acres,
            soil_type=soil_type,
            location=location,
            recommended_crop=best_crop.crop_name,
            comparison=items,
            decision_rationale=rationale
        )

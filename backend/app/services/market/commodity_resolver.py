from typing import List, Dict, Tuple, Optional
from decimal import Decimal

# Canonical Agmarknet commodity naming aliases
COMMODITY_ALIASES: Dict[str, List[str]] = {
    "chilli": ["Chilli(Dry)", "Chilli Red", "Chilli", "Dry Chillies", "Chilli(Green)"],
    "dry chilli": ["Chilli(Dry)", "Chilli Red", "Dry Chillies"],
    "green chilli": ["Chilli(Green)", "Green Chilli"],
    "red chilli": ["Chilli(Dry)", "Chilli Red", "Chilli"],
    "mirchi": ["Chilli(Dry)", "Chilli Red", "Chilli"],
    "మిర్చి": ["Chilli(Dry)", "Chilli Red", "Chilli"],
    "मिर्च": ["Chilli(Dry)", "Chilli Red", "Chilli"],
    "cotton": ["Cotton", "Cotton(Unginned)", "Kapas"],
    "kapas": ["Cotton", "Cotton(Unginned)", "Kapas"],
    "పత్తి": ["Cotton", "Cotton(Unginned)", "Kapas"],
    "कपास": ["Cotton", "Cotton(Unginned)", "Kapas"],
    "soybean": ["Soyabean", "Soybean"],
    "paddy": ["Paddy(Common)", "Paddy(Dhan)", "Paddy"],
    "rice": ["Paddy(Common)", "Paddy(Dhan)", "Rice"],
    "వరి": ["Paddy(Common)", "Paddy(Dhan)", "Rice"],
    "धान": ["Paddy(Common)", "Paddy(Dhan)", "Rice"],
    "चावल": ["Paddy(Common)", "Paddy(Dhan)", "Rice"],
    "maize": ["Maize", "Makka"],
    "corn": ["Maize", "Makka"],
    "మొక్కజొన్న": ["Maize", "Makka"],
    "मक्का": ["Maize", "Makka"],
    "turmeric": ["Turmeric", "Turmeric(Whole)"],
    "పసుపు": ["Turmeric", "Turmeric(Whole)"],
    "हल्दी": ["Turmeric", "Turmeric(Whole)"],
    "bengal gram": ["Bengal Gram(Gram)(Whole)", "Gram(Whole)"],
    "chana": ["Bengal Gram(Gram)(Whole)", "Gram(Whole)"],
    "శనగలు": ["Bengal Gram(Gram)(Whole)", "Gram(Whole)"],
    "चना": ["Bengal Gram(Gram)(Whole)", "Gram(Whole)"],
    "groundnut": ["Groundnut", "Groundnut Pods (Raw)"],
    "peanut": ["Groundnut", "Groundnut Pods (Raw)"],
    "వేరుశనగ": ["Groundnut", "Groundnut Pods (Raw)"],
    "मूंगफली": ["Groundnut", "Groundnut Pods (Raw)"],
    "castor seed": ["Castor Seed"],
    "jowar": ["Jowar(Sorghum)", "Jowar(White)"],
    "sorghum": ["Jowar(Sorghum)", "Jowar(White)"],
    "జొన్నలు": ["Jowar(Sorghum)", "Jowar(White)"],
    "potato": ["Potato"],
    "aloo": ["Potato"],
    "బంగాళాదుంప": ["Potato"],
    "आलू": ["Potato"],
    "tomato": ["Tomato"],
    "tamatar": ["Tomato"],
    "టమోటా": ["Tomato"],
    "టమాట": ["Tomato"],
    "टमाटर": ["Tomato"],
    "onion": ["Onion"],
    "pyaz": ["Onion"],
    "ఉల్లిపాయ": ["Onion"],
    "प्याज": ["Onion"],
    "banana": ["Banana"],
    "kela": ["Banana"],
    "అరటి": ["Banana"],
    "केला": ["Banana"],
    "wheat": ["Wheat"],
    "gehu": ["Wheat"],
    "గోధుమ": ["Wheat"],
    "गेहूं": ["Wheat"],
    "red gram": ["Red Gram", "Arhar (Tur/Red Gram)(Whole)"],
    "arhar": ["Red Gram", "Arhar (Tur/Red Gram)(Whole)"],
    "tur": ["Red Gram", "Arhar (Tur/Red Gram)(Whole)"],
    "కందులు": ["Red Gram", "Arhar (Tur/Red Gram)(Whole)"],
    "अरहर": ["Red Gram", "Arhar (Tur/Red Gram)(Whole)"]
}

def resolve_commodity_search_terms(commodity: str) -> List[str]:
    """Returns candidate query names for a given informal or farmer-entered commodity."""
    key = commodity.strip().lower()
    if key in COMMODITY_ALIASES:
        return COMMODITY_ALIASES[key]
    # Fallback to capitalized original query
    return [commodity.strip().title(), commodity.strip()]

def estimate_mandi_logistics(
    farmer_district: str,
    mandi_district: str,
    mandi_name: str
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Estimates (distance_km, transport_cost_per_quintal, selling_cost_per_quintal)
    between farmer's registered location and a target APMC mandi.
    Uses conservative standard freight rate formulas for agricultural dispatch.
    """
    f_dist = farmer_district.strip().lower()
    m_dist = mandi_district.strip().lower()

    if f_dist == m_dist:
        # Local benchmark APMC within home district
        distance = Decimal("15.0")
        transport = Decimal("80.00")
        selling_fee = Decimal("20.00")
    elif any(n in m_dist for n in ("khammam", "krishna", "prakasam", "ntr", "guntur")):
        # Adjacent district regional APMC
        distance = Decimal("110.0")
        transport = Decimal("380.00")
        selling_fee = Decimal("30.00")
    else:
        # Distant terminal APMC
        distance = Decimal("180.0")
        transport = Decimal("520.00")
        selling_fee = Decimal("40.00")

    return distance, transport, selling_fee

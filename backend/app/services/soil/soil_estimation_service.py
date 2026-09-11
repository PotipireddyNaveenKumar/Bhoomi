"""
BHOOMI V2 — Location-Based Soil Estimation & Provenance Service

Provides location-based soil estimates based on Indian state, district, or coordinates
using ICAR-NBSS&LUP (National Bureau of Soil Survey and Land Use Planning) agro-ecological
data and regional Soil Health Card benchmarks.

CRITICAL POLICY:
- Explicitly states: "Estimated from location"
- Estimated values include: estimated pH, estimated soil type, soil texture & characteristics,
  source ("ICAR-NBSS&LUP Regional Agro-Ecological Survey"), and confidence.
- N, P, and K are NOT fabricated from location alone:
  Explicitly reports: "N/P/K soil-test values not available from location alone."
- All values carry complete provenance: source_type ("estimated" vs "farmer_entered" / "measured"),
  source, confidence, and location.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SoilValueProvenance(BaseModel):
    value: Optional[float] = None
    display_value: str = "Not Available"
    source_type: str = "estimated"  # "estimated" | "farmer_entered" | "measured" | "not_available_from_location"
    source: str = "ICAR-NBSS&LUP Agro-Ecological Atlas"
    confidence: float = 0.85
    notes: str = ""


class SoilEstimateResponse(BaseModel):
    state: str
    district: str
    soil_type: str
    soil_type_local: Dict[str, str] = Field(default_factory=dict)
    estimated_ph: float
    ph_range: str
    soil_texture: str
    organic_carbon_status: str
    water_retention_capacity: str
    source: str
    source_authority: str
    confidence: float
    is_laboratory_measured: bool = False
    disclaimer: str
    npk_available: bool = False
    npk_notice: str
    provenance: Dict[str, Any] = Field(default_factory=dict)


# Authoritative district-level soil mapping from ICAR-NBSS&LUP Agro-Ecological Sub-Regions
REGIONAL_SOIL_DATABASE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Andhra Pradesh": {
        "Guntur": {
            "soil_type": "black",
            "soil_type_local": {"te": "నల్లరేగడి నేల (Vertisols)", "hi": "काली मिट्टी (कपास मृदा)", "en": "Deep Black Cotton Soil"},
            "ph": 7.8,
            "ph_range": "7.5 - 8.2 (Moderately Alkaline)",
            "texture": "Clay loam to Heavy Clay (Vertisols)",
            "organic_carbon": "Medium (0.45 - 0.60%)",
            "water_retention": "High (holds moisture for 10-14 days)",
            "confidence": 0.90,
            "notes": "Excellent for Chilli (Teja), Cotton, and Bengal Gram. Vulnerable to waterlogging if drainage is inadequate."
        },
        "Krishna": {
            "soil_type": "alluvial",
            "soil_type_local": {"te": "ఒండ్రు నేల (Alluvial)", "hi": "जलोढ़ मिट्टी", "en": "Deltaic Alluvial Soil"},
            "ph": 7.2,
            "ph_range": "6.8 - 7.6 (Neutral)",
            "texture": "Silty clay to Clay loam",
            "organic_carbon": "Medium to High (0.60 - 0.75%)",
            "water_retention": "High",
            "confidence": 0.88,
            "notes": "Krishna delta alluvial plain. High fertility for Paddy, Sugarcane, and Pulses."
        },
        "Prakasam": {
            "soil_type": "red",
            "soil_type_local": {"te": "ఎర్ర నేల (Alfisols)", "hi": "लाल दोमट मिट्टी", "en": "Red Sandy Loam"},
            "ph": 6.8,
            "ph_range": "6.2 - 7.2 (Slightly Acidic to Neutral)",
            "texture": "Sandy loam to Loamy sand",
            "organic_carbon": "Low to Medium (0.35 - 0.50%)",
            "water_retention": "Low to Moderate (requires frequent irrigation)",
            "confidence": 0.85,
            "notes": "Suited for Tobacco, Groundnut, Pulses, and Chilli with drip irrigation."
        },
        "Kurnool": {
            "soil_type": "black",
            "soil_type_local": {"te": "నల్లరేగడి నేల", "hi": "काली मिट्टी", "en": "Medium Black Soil"},
            "ph": 7.9,
            "ph_range": "7.5 - 8.3",
            "texture": "Clay loam",
            "organic_carbon": "Low to Medium (0.40 - 0.55%)",
            "water_retention": "High",
            "confidence": 0.87,
            "notes": "Rayalaseema black soil zone. Good for Sunflower, Cotton, and Bengal Gram."
        },
        "Anantapur": {
            "soil_type": "red",
            "soil_type_local": {"te": "ఎర్ర ఇసుక నేల", "hi": "लाल बलुई मिट्टी", "en": "Red Sandy Loam"},
            "ph": 6.9,
            "ph_range": "6.4 - 7.4",
            "texture": "Coarse sandy loam",
            "organic_carbon": "Low (< 0.35%)",
            "water_retention": "Low",
            "confidence": 0.86,
            "notes": "Semi-arid drought-prone tract. Groundnut, Millets, and Pomegranate with micro-irrigation."
        }
    },
    "Telangana": {
        "Warangal": {
            "soil_type": "red",
            "soil_type_local": {"te": "ఎర్ర నేల (చల్కా నేలలు)", "hi": "लाल दोमट मिट्टी", "en": "Red Loamy Soil (Chalka)"},
            "ph": 6.6,
            "ph_range": "6.0 - 7.2 (Near Neutral)",
            "texture": "Sandy clay loam",
            "organic_carbon": "Medium (0.45 - 0.55%)",
            "water_retention": "Moderate",
            "confidence": 0.89,
            "notes": "Widely occurring chalka soil. Highly responsive to organic manure; suited for Cotton, Chilli, Maize, and Paddy."
        },
        "Karimnagar": {
            "soil_type": "black",
            "soil_type_local": {"te": "నల్లరేగడి నేల", "hi": "काली मिट्टी", "en": "Deep Black Soil"},
            "ph": 7.7,
            "ph_range": "7.3 - 8.1",
            "texture": "Clay loam",
            "organic_carbon": "Medium (0.50 - 0.65%)",
            "water_retention": "High",
            "confidence": 0.88,
            "notes": "Godavari basin black tract. Excellent for Paddy, Cotton, and Maize."
        },
        "Nalgonda": {
            "soil_type": "red",
            "soil_type_local": {"te": "ఎర్ర ఇసుక నేల", "hi": "लाल बलुई मिट्टी", "en": "Red Sandy Soil"},
            "ph": 7.1,
            "ph_range": "6.5 - 7.6",
            "texture": "Sandy loam",
            "organic_carbon": "Low (0.30 - 0.45%)",
            "water_retention": "Low to Moderate",
            "confidence": 0.86,
            "notes": "Sweet lime (Mosambi), Cotton, Paddy (Nagarjuna Sagar command), and Castor."
        },
        "Khammam": {
            "soil_type": "alluvial",
            "soil_type_local": {"te": "నల్లరేగడి / ఒండ్రు నేల", "hi": "काली व जलोढ़ मिट्टी", "en": "Black and Alluvial Soil"},
            "ph": 7.4,
            "ph_range": "7.0 - 7.8",
            "texture": "Clay to Clay loam",
            "organic_carbon": "Medium (0.55 - 0.70%)",
            "water_retention": "High",
            "confidence": 0.88,
            "notes": "Very fertile belt for Chilli, Cotton, Paddy, and Mango plantations."
        },
        "Nizamabad": {
            "soil_type": "black",
            "soil_type_local": {"te": "నల్లరేగడి నేల", "hi": "काली मिट्टी", "en": "Medium to Deep Black Soil"},
            "ph": 7.6,
            "ph_range": "7.2 - 8.0",
            "texture": "Clayey",
            "organic_carbon": "Medium (0.50 - 0.60%)",
            "water_retention": "High",
            "confidence": 0.87,
            "notes": "Soybean, Turmeric, Sugarcane, and Paddy."
        }
    },
    "Karnataka": {
        "Dharwad": {
            "soil_type": "black",
            "soil_type_local": {"kn": "ಕಪ್ಪು ಮಣ್ಣು (Black Soil)", "en": "Medium to Deep Black Cotton Soil"},
            "ph": 7.8,
            "ph_range": "7.4 - 8.2",
            "texture": "Clayey (Vertisols)",
            "organic_carbon": "Medium (0.45 - 0.60%)",
            "water_retention": "High",
            "confidence": 0.89,
            "notes": "North Karnataka black soil zone. Suited for Cotton, Bengal Gram, Maize, and Jowar."
        },
        "Belagavi": {
            "soil_type": "black",
            "soil_type_local": {"kn": "ಕಪ್ಪು ಮಣ್ಣು", "en": "Deep Black Alluvial Soil"},
            "ph": 7.5,
            "ph_range": "7.1 - 7.9",
            "texture": "Clay loam",
            "organic_carbon": "Medium to High (0.60 - 0.75%)",
            "water_retention": "High",
            "confidence": 0.88,
            "notes": "Major Sugarcane, Soybean, Maize, and Vegetable production hub."
        },
        "Mysuru": {
            "soil_type": "red",
            "soil_type_local": {"kn": "ಕೆಂಪು ಮಣ್ಣು (Red Soil)", "en": "Red Sandy Loam to Clay Loam"},
            "ph": 6.5,
            "ph_range": "5.8 - 7.0 (Slightly Acidic)",
            "texture": "Sandy clay loam",
            "organic_carbon": "Medium (0.50 - 0.65%)",
            "water_retention": "Moderate",
            "confidence": 0.87,
            "notes": "Southern dry zone. Suited for Ragi (Finger Millet), Pulses, Sugarcane, and Banana."
        }
    },
    "Tamil Nadu": {
        "Coimbatore": {
            "soil_type": "red",
            "soil_type_local": {"ta": "செம்மண் (Red Loam)", "en": "Red Loam to Calcareous Black Soil"},
            "ph": 7.2,
            "ph_range": "6.8 - 7.6",
            "texture": "Loamy to Sandy clay loam",
            "organic_carbon": "Low to Medium (0.40 - 0.55%)",
            "water_retention": "Moderate",
            "confidence": 0.88,
            "notes": "Western agro-climatic zone. Cotton, Maize, Vegetables, Banana, and Turmeric."
        },
        "Thanjavur": {
            "soil_type": "alluvial",
            "soil_type_local": {"ta": "வண்டல் மண் (Alluvial)", "en": "Cauvery Delta Alluvial Soil"},
            "ph": 7.1,
            "ph_range": "6.7 - 7.5",
            "texture": "Clayey alluvial",
            "organic_carbon": "Medium to High (0.65 - 0.80%)",
            "water_retention": "High",
            "confidence": 0.90,
            "notes": "Granary of South India. Triple-crop Paddy, Black Gram, and Coconut."
        }
    },
    "Maharashtra": {
        "Nashik": {
            "soil_type": "black",
            "soil_type_local": {"mr": "काळी मृदा (Black Soil)", "en": "Medium Black Soil"},
            "ph": 7.4,
            "ph_range": "7.0 - 7.8",
            "texture": "Clay loam to Loamy",
            "organic_carbon": "Medium (0.50 - 0.65%)",
            "water_retention": "High",
            "confidence": 0.90,
            "notes": "Deccan black soil. Prime tract for Grapes, Onion, Tomato, and Pomegranate."
        },
        "Nagpur": {
            "soil_type": "black",
            "soil_type_local": {"mr": "भारी काळी माती", "en": "Deep Vertisols (Black Cotton Soil)"},
            "ph": 7.9,
            "ph_range": "7.5 - 8.3",
            "texture": "Heavy clay",
            "organic_carbon": "Medium (0.45 - 0.60%)",
            "water_retention": "Very High",
            "confidence": 0.91,
            "notes": "Vidarbha black soil. World famous for Nagpur Mandarin Orange, Cotton, and Soybean."
        }
    },
    "Punjab": {
        "Ludhiana": {
            "soil_type": "alluvial",
            "soil_type_local": {"en": "Indo-Gangetic Alluvial Loam"},
            "ph": 7.6,
            "ph_range": "7.2 - 8.0",
            "texture": "Silt loam to Sandy loam",
            "organic_carbon": "Medium (0.40 - 0.55%)",
            "water_retention": "Moderate to High",
            "confidence": 0.92,
            "notes": "Indo-Gangetic plain. Intensive Wheat-Rice rotation and Potato seed multiplication."
        }
    },
    "Uttar Pradesh": {
        "Varanasi": {
            "soil_type": "alluvial",
            "soil_type_local": {"hi": "जलोढ़ दोमट मिट्टी", "en": "Gangetic Alluvial Loam"},
            "ph": 7.3,
            "ph_range": "6.9 - 7.7",
            "texture": "Sandy loam to Silt loam",
            "organic_carbon": "Medium (0.45 - 0.60%)",
            "water_retention": "Moderate to High",
            "confidence": 0.89,
            "notes": "Middle Gangetic plains. Highly fertile for Rice, Wheat, Vegetables (Tomato, Brinjal), and Pulses."
        }
    }
}

# Generic fallback based on state agro-ecological classification
STATE_GENERIC_SOILS: Dict[str, Dict[str, Any]] = {
    "Andhra Pradesh": {"soil_type": "black", "ph": 7.6, "ph_range": "7.2 - 8.0", "texture": "Clay loam", "confidence": 0.75},
    "Telangana": {"soil_type": "red", "ph": 6.8, "ph_range": "6.2 - 7.4", "texture": "Sandy clay loam", "confidence": 0.75},
    "Karnataka": {"soil_type": "red", "ph": 6.7, "ph_range": "6.0 - 7.2", "texture": "Red loam", "confidence": 0.75},
    "Tamil Nadu": {"soil_type": "red", "ph": 7.0, "ph_range": "6.5 - 7.5", "texture": "Sandy loam", "confidence": 0.75},
    "Maharashtra": {"soil_type": "black", "ph": 7.7, "ph_range": "7.2 - 8.2", "texture": "Clayey Vertisols", "confidence": 0.78},
    "Punjab": {"soil_type": "alluvial", "ph": 7.6, "ph_range": "7.2 - 8.0", "texture": "Alluvial loam", "confidence": 0.80},
    "Haryana": {"soil_type": "alluvial", "ph": 7.7, "ph_range": "7.3 - 8.1", "texture": "Sandy loam to Loam", "confidence": 0.78},
    "Uttar Pradesh": {"soil_type": "alluvial", "ph": 7.4, "ph_range": "7.0 - 7.8", "texture": "Gangetic alluvial", "confidence": 0.80},
    "Madhya Pradesh": {"soil_type": "black", "ph": 7.6, "ph_range": "7.2 - 8.0", "texture": "Medium black soil", "confidence": 0.75},
    "Rajasthan": {"soil_type": "sandy", "ph": 8.0, "ph_range": "7.6 - 8.4", "texture": "Desert sandy soil", "confidence": 0.75},
    "Gujarat": {"soil_type": "black", "ph": 7.8, "ph_range": "7.4 - 8.2", "texture": "Clay loam", "confidence": 0.75},
    "West Bengal": {"soil_type": "alluvial", "ph": 6.5, "ph_range": "5.8 - 7.2", "texture": "Deltaic silt loam", "confidence": 0.78},
    "Bihar": {"soil_type": "alluvial", "ph": 7.2, "ph_range": "6.8 - 7.6", "texture": "Silty clay loam", "confidence": 0.78},
    "Odisha": {"soil_type": "red", "ph": 6.2, "ph_range": "5.5 - 6.8", "texture": "Red and yellow soil", "confidence": 0.75},
    "Kerala": {"soil_type": "laterite", "ph": 5.4, "ph_range": "4.8 - 6.0 (Acidic)", "texture": "Laterite gravelly loam", "confidence": 0.80},
}


class SoilEstimationService:
    """
    Core service delivering location-based soil characteristics and provenance tracking.
    """

    @classmethod
    def get_soil_estimate(
        cls,
        state: Optional[str] = None,
        district: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> SoilEstimateResponse:
        clean_state = (state or "Telangana").strip().title()
        clean_district = (district or "Warangal").strip().title()

        # Coordinates lookup heuristic for southern/central regions if state omitted
        if (not state or state == "India") and latitude and longitude:
            if 15.5 <= latitude <= 19.5 and 77.0 <= longitude <= 81.5:
                clean_state = "Telangana"
                clean_district = "Warangal"
            elif 13.5 <= latitude <= 19.0 and 79.5 <= longitude <= 84.5:
                clean_state = "Andhra Pradesh"
                clean_district = "Guntur"
            elif 18.0 <= latitude <= 21.5 and 72.5 <= longitude <= 80.5:
                clean_state = "Maharashtra"
                clean_district = "Nashik"

        # Lookup in regional database
        district_data = None
        state_dict = REGIONAL_SOIL_DATABASE.get(clean_state)
        if state_dict:
            district_data = state_dict.get(clean_district)
            if not district_data:
                # Fuzzy district search
                for d_name, d_val in state_dict.items():
                    if d_name.lower() in clean_district.lower() or clean_district.lower() in d_name.lower():
                        district_data = d_val
                        clean_district = d_name
                        break

        if not district_data:
            generic = STATE_GENERIC_SOILS.get(clean_state, {
                "soil_type": "black",
                "ph": 7.2,
                "ph_range": "6.8 - 7.6",
                "texture": "Loamy soil",
                "confidence": 0.70
            })
            district_data = {
                "soil_type": generic["soil_type"],
                "soil_type_local": {"en": f"{generic['soil_type'].title()} Soil"},
                "ph": generic["ph"],
                "ph_range": generic["ph_range"],
                "texture": generic["texture"],
                "organic_carbon": "Moderate (0.45 - 0.60%)",
                "water_retention": "Moderate",
                "confidence": generic["confidence"],
                "notes": f"Regional agro-ecological soil estimate for {clean_state}."
            }

        provenance = {
            "soil_type": {
                "value": district_data["soil_type"],
                "source_type": "estimated",
                "source": "ICAR-NBSS&LUP Agro-Ecological Sub-Regions of India",
                "confidence": district_data["confidence"]
            },
            "pH": {
                "value": district_data["ph"],
                "display_value": str(district_data["ph"]),
                "source_type": "estimated",
                "source": "ICAR-NBSS&LUP Soil Health Benchmark",
                "confidence": district_data["confidence"],
                "range": district_data["ph_range"]
            },
            "nitrogen": {
                "value": None,
                "display_value": "Not Available from Location",
                "source_type": "not_available_from_location",
                "source": "Laboratory test required",
                "confidence": 0.0
            },
            "phosphorus": {
                "value": None,
                "display_value": "Not Available from Location",
                "source_type": "not_available_from_location",
                "source": "Laboratory test required",
                "confidence": 0.0
            },
            "potassium": {
                "value": None,
                "display_value": "Not Available from Location",
                "source_type": "not_available_from_location",
                "source": "Laboratory test required",
                "confidence": 0.0
            }
        }

        return SoilEstimateResponse(
            state=clean_state,
            district=clean_district,
            soil_type=district_data["soil_type"],
            soil_type_local=district_data.get("soil_type_local", {}),
            estimated_ph=district_data["ph"],
            ph_range=district_data["ph_range"],
            soil_texture=district_data["texture"],
            organic_carbon_status=district_data["organic_carbon"],
            water_retention_capacity=district_data["water_retention"],
            source="ICAR-NBSS&LUP Regional Agro-Ecological Survey",
            source_authority="Indian Council of Agricultural Research (ICAR)",
            confidence=district_data["confidence"],
            is_laboratory_measured=False,
            disclaimer="Estimated from location. These are regional agro-ecological indicators, NOT laboratory soil-test measurements.",
            npk_available=False,
            npk_notice="N/P/K soil-test values not available from location alone. Please enter values from your Soil Health Card if available.",
            provenance=provenance
        )

"""
Query Understanding & Normalization Service for BHOOMI Agricultural RAG.
Extracts canonical agrarian entities, language, intent, symptoms, pests, diseases,
crop, soil, location, and phenological stage from farmer queries across 6 languages:
English (en), Telugu (te), Hindi (hi), Tamil (ta), Kannada (kn), Malayalam (ml).

Strict Grounding Rule: Never fabricate missing information (crop=None, location=None if not in query/context).
"""
import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.core.logging import logger


class QueryUnderstandingResult(BaseModel):
    original_query: str
    normalized_query: str
    language: str = "en"
    intent: str = "GENERAL_AGRICULTURE"
    crop: Optional[str] = None
    crop_variety: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    disease: Optional[str] = None
    pest: Optional[str] = None
    soil: Optional[str] = None
    growth_stage: Optional[str] = None
    topic: Optional[str] = None
    location: Optional[Dict[str, Optional[str]]] = None  # {"state": ..., "district": ...}
    time_context: Optional[str] = None
    is_live_query: bool = False
    requires_rag: bool = True
    confidence: float = 0.90


class QueryUnderstandingService:
    """
    Multilingual agrarian entity extractor & query normalizer.
    """

    # Multilingual Crop Dictionaries
    CROPS = {
        "chilli": [
            "chilli", "chilli crop", "chillies", "chili", "mirchi", "pepper", "peppers",
            "మిరప", "మిర్చి", "మిరపకాయ", "మిరప తోట", "మిరప పంట",
            "मिर्च", "मिर्ची", "हरी मिर्च", "लाल मिर्च",
            "மிளகாய்", "ಮೆಣಸಿನಕಾಯಿ", "മുളക്"
        ],
        "tomato": [
            "tomato", "tomatoes", "tamatar",
            "టమాటా", "టమోటా", "టమాట", "రామములక్కాయ",
            "टमाटर", "तमाटर",
            "தக்காளி", "ಟೊಮೆಟೊ", "തക്കാളി"
        ],
        "cotton": [
            "cotton", "kapas",
            "పత్తి", "దూది", "పత్తి తోట", "పత్తి పంట",
            "कपास", "कपास की फसल", "रुई",
            "பருத்தி", "ಹತ್ತಿ", "പരുത്തി"
        ],
        "rice": [
            "rice", "paddy", "dhan",
            "వరి", "వరి పంట", "వరి తోట", "వరి చేను", "వరి ధాన్యం",
            "धान", "चावल", "धान की फसल",
            "நெல்", "ಭತ್ತ", "നെല്ല്"
        ],
        "wheat": [
            "wheat", "gehun",
            "గోధుమ", "గోధుమలు",
            "गेहूं", "गेंहू",
            "கோதுமை", "ಗೋಧಿ", "ഗോതമ്പ്"
        ],
        "corn_maize": [
            "maize", "corn", "makka", "makai",
            "మొక్కజొన్న", "జొన్న",
            "मक्का", "मकई",
            "மக்காச்சோளம்", "ಮೆಕ್ಕೆಜೋಳ", "മക്കച്ചോളം"
        ],
        "potato": [
            "potato", "potatoes", "aloo",
            "బంగాళాదుంప", "ఆలూ",
            "आलू",
            "உருளைக்கிழங்கு", "ಆಲೂಗಡ್ಡೆ", "ഉരുളക്കിഴങ്ങ്"
        ],
        "banana": [
            "banana", "kela",
            "అరటి", "అరటి తోట",
            "केला",
            "வாழை", "ಬಾಳೆ", "വാഴ"
        ],
        "groundnut": [
            "groundnut", "peanut", "moongphali",
            "వేరుశనగ", "పల్లీ", "వేరుశెనగ",
            "मूंगफली",
            "நிலக்கடலை", "ಕಡಲೆಕಾಯಿ", "നിലക്കടല"
        ],
        "soybean": [
            "soybean", "soya",
            "సోయాబీన్", "సోయా",
            "सोयाबीन",
            "சோயாபீன்", "ಸೋಯಾಬೀನ್", "സോയാബീൻ"
        ],
        "sugarcane": [
            "sugarcane", "cane", "ganna",
            "చెరకు", "గన్న", "చెరకు తోట",
            "गन्ना", "गन्ने",
            "கரும்பு", "ಕಬ್ಬು", "കരിമ്പ്"
        ],
        "apple": [
            "apple", "apples", "seb",
            "సేపు", "యాపిల్", "ఆపిల్",
            "सेब", "सेब का बगीचा",
            "ஆப்பிள்", "ಸೇಬು", "ആപ്പിൾ"
        ]
    }

    # Multilingual Symptoms
    SYMPTOMS = {
        "leaf_curling": [
            "curl", "curling", "curled", "puckering", "leaf curl",
            "ముడుచుకుంటున్నాయి", "ముడుచుకుంటుంది", "ముడుచు", "ముడత", "ఆకు ముడత", "ఆకులు ముడుచు",
            "ముడుచుకోవడం", "ముడుచుకు",
            "मुड़ रहे हैं", "मुड़ रही", "मुड़ना", "पत्ती मुड़", "पत्तियां मुड़", "मरोड़िया", "सिकुड़ना",
            "சுருட்டை", "இலை சுருட்டை", "ಮುದುಡುವಿಕೆ", "ಎಲೆ ಮುದುಡುವುದು", "ചുരുളൽ"
        ],
        "yellowing_chlorosis": [
            "yellow", "yellowing", "yellow leaves", "chlorosis", "pale leaves",
            "పసుపు", "పసుపు రంగు", "ఆకులు పసుపు", "పసుపు పచ్చ",
            "पीली", "पीला", "पीले पत्ते", "पीलापन",
            "மஞ்சள்", "ಹಳದಿ", "മഞ്ഞളിപ്പ്"
        ],
        "spots_blight": [
            "spot", "spots", "brown spots", "black spots", "blight", "lesions",
            "మచ్చలు", "నల్ల మచ్చలు", "గోధుమ మచ్చలు", "ఆకుమచ్చ", "తెగులు",
            "धब्बे", "काले धब्बे", "भूरे धब्बे", "झुलसा", "ब्लाइट",
            "புள்ளிகள்", "ಚುಕ್ಕೆಗಳು", "പുള്ളികൾ"
        ],
        "wilting": [
            "wilt", "wilting", "drooping", "drying",
            "ఎండిపోవడం", "వడలిపోవడం", "వాలిపోవడం",
            "मुरझाना", "सूखना",
            "வாடல்", "ಬಾಡುವುದು", "വാട്ടം"
        ],
        "fruit_rot": [
            "rot", "fruit rot", "rotting", "pod rot",
            "కుళ్లు", "కాయ కుళ్లు", "మొగ్గ కుళ్లు",
            "सड़न", "गलना", "फल सड़न",
            "அழுகல்", "ಕೊಳೆತ", "ചീയൽ"
        ]
    }

    # Multilingual Pests
    PESTS = {
        "thrips": ["thrips", "తామర పురుగు", "తామర పురుగులు", "తామర", "थ्रिप्स", "इल्ली"],
        "mites": ["mites", "yellow mites", "నల్లి", "పల్చటి నల్లి", "మైట్స్", "माइट्स"],
        "whitefly": ["whitefly", "whiteflies", "తెల్లదోమ", "దోమ", "सफेद मक्खी"],
        "borer": ["borer", "bollworm", "caterpillar", "కాయ తొలుచు పురుగు", "గులాబీ రంగు పురుగు", "సుండి", "इल्ली", "छेदक"],
        "planthopper": ["bph", "brown planthopper", "hopper", "సుడిదోమ", "भूरा फुदका"]
    }

    # Multilingual Soils
    SOILS = {
        "black_cotton_soil": ["black soil", "black cotton", "vertisols", "నల్లరేగడి", "నల్ల రేగడి", "నల్ల నేల", "काली मिट्टी", "काली कपास मृदा"],
        "red_sandy_loam": ["red soil", "alfisols", "sandy loam", "ఎర్ర నేల", "ఎర్ర మట్టి", "लाल मिट्टी"],
        "alluvial_soil": ["alluvial soil", "గండ నేల", "వరి నేల", "जलोढ़ मिट्टी"],
        "saline_alkaline_soil": ["saline soil", "alkaline soil", "usar", "salt soil", "చౌడు నేల", "ఉప్పు నేల", "क्षारीय मृदा", "लवणीय मिट्टी"]
    }

    # District & State Mapping
    LOCATIONS = {
        "guntur": {"district": "Guntur", "state": "Andhra Pradesh"},
        "prakasam": {"district": "Prakasam", "state": "Andhra Pradesh"},
        "kurnool": {"district": "Kurnool", "state": "Andhra Pradesh"},
        "anantapur": {"district": "Anantapur", "state": "Andhra Pradesh"},
        "krishna": {"district": "Krishna", "state": "Andhra Pradesh"},
        "warangal": {"district": "Warangal", "state": "Telangana"},
        "khammam": {"district": "Khammam", "state": "Telangana"},
        "nagpur": {"district": "Nagpur", "state": "Maharashtra"},
        "andhra pradesh": {"district": None, "state": "Andhra Pradesh"},
        "telangana": {"district": None, "state": "Telangana"},
        "గుంటూరు": {"district": "Guntur", "state": "Andhra Pradesh"},
        "ప్రకాశం": {"district": "Prakasam", "state": "Andhra Pradesh"},
        "కర్నూలు": {"district": "Kurnool", "state": "Andhra Pradesh"},
        "గుంటూరులో": {"district": "Guntur", "state": "Andhra Pradesh"},
        "गुंटूर": {"district": "Guntur", "state": "Andhra Pradesh"}
    }

    @classmethod
    def detect_language(cls, text: str) -> str:
        # Check script ranges
        has_telugu = bool(re.search(r'[\u0C00-\u0C7F]', text))
        if has_telugu:
            return "te"
        has_hindi = bool(re.search(r'[\u0900-\u097F]', text))
        if has_hindi:
            return "hi"
        has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
        if has_tamil:
            return "ta"
        has_kannada = bool(re.search(r'[\u0C80-\u0CFF]', text))
        if has_kannada:
            return "kn"
        has_malayalam = bool(re.search(r'[\u0D00-\u0D7F]', text))
        if has_malayalam:
            return "ml"
        return "en"

    @classmethod
    def understand(
        cls,
        query: str,
        farmer_context: Optional[Dict[str, Any]] = None
    ) -> QueryUnderstandingResult:
        query_clean = query.strip()
        query_lower = query_clean.lower()
        lang = cls.detect_language(query_clean)

        # 1. Extract Crop
        extracted_crop = None
        for canonical, aliases in cls.CROPS.items():
            for alias in aliases:
                if alias in query_lower:
                    extracted_crop = canonical
                    break
            if extracted_crop:
                break

        # Fallback to farm context active crop ONLY if query has foliar/symptom/crop intent
        # but did not mention crop explicitly
        context_crop = None
        if farmer_context and farmer_context.get("active_crops"):
            ac = farmer_context["active_crops"][0]
            context_crop = ac.get("crop_name", "").lower() if isinstance(ac, dict) else str(ac).lower()

        # 2. Extract Symptoms
        extracted_symptoms = []
        for sym_name, sym_aliases in cls.SYMPTOMS.items():
            for alias in sym_aliases:
                if alias in query_lower:
                    extracted_symptoms.append(sym_name)
                    break

        # 3. Extract Pests
        extracted_pest = None
        for pest_name, pest_aliases in cls.PESTS.items():
            for alias in pest_aliases:
                if alias in query_lower:
                    extracted_pest = pest_name
                    break
            if extracted_pest:
                break

        # 4. Extract Soil
        extracted_soil = None
        for soil_name, soil_aliases in cls.SOILS.items():
            for alias in soil_aliases:
                if alias in query_lower:
                    extracted_soil = soil_name
                    break
            if extracted_soil:
                break

        # 5. Extract Location
        extracted_loc = None
        for loc_key, loc_val in cls.LOCATIONS.items():
            if loc_key in query_lower:
                extracted_loc = loc_val.copy()
                break

        # Fallback location from farm context if query didn't specify one
        if not extracted_loc and farmer_context and farmer_context.get("location"):
            fl = farmer_context["location"]
            if isinstance(fl, dict):
                extracted_loc = {"state": fl.get("state"), "district": fl.get("district")}

        # 6. Classify Intent & Topic
        intent = "GENERAL_AGRICULTURE"
        topic = "agronomy"
        is_live_query = False
        requires_rag = True

        # Check for Live Market Tool queries (Step 14: RAG vs Live Tool Separation)
        is_market = any(w in query_lower for w in ["price", "market", "mandi", "rate", "modal", "ధర", "మార్కెట్", "మండి", "दाम", "भाव", "மண்டி", "വില"])
        is_sell_decision = any(w in query_lower for w in ["sell now", "should i sell", "when to sell", "అమ్మాలా", "అమ్మవచ్చా", "बेचें", "बेचना चाहिए"])

        # Check for Live Weather Tool queries
        is_weather = any(w in query_lower for w in ["weather", "will it rain", "rain forecast", "rainfall", "temperature", "వాతావరణం", "వర్షం", "मौसम", "बारिश", "மழை"])

        # Check for Spray Weather Safety
        is_spray = any(w in query_lower for w in ["spray", "spraying", "herbicide", "pesticide", "fungicide", "పిచికారీ", "స్ప్రే", "మందు కొట్ట", "छिड़काव", "स्प्रे"])
        is_spray_weather = is_spray and (is_weather or any(w in query_lower for w in ["tomorrow", "morning", "today", "safe to", "can i", "రేపు", "ఉదయం", "చేయవచ్చా", "कल", "सुबह"]))

        # Check for Profit / Economics
        is_profit = any(w in query_lower for w in ["profit", "net profit", "revenue", "how much profit", "లాభం", "ఎంత లాభం", "ఆదాయం", "मुनाफा", "आमदनी"])

        # Check for Government Schemes
        is_scheme = any(w in query_lower for w in ["pm-kisan", "pm kisan", "scheme", "subsidy", "pmfby", "crop insurance", "kcc", "పథకం", "సబ్సిడీ", "భీమా", "योजना", "सब्सिडी", "बीमा"])

        # Check for Irrigation
        is_irrig = any(w in query_lower for w in ["irrigate", "irrigation", "water the crop", "when to irrigate", "నీరు పెట్టాలా", "తడి ఇవ్వాలా", "సిరచాల", "నీటి పారుదల", "सिंचाई", "पानी देना"])

        # Check for Fertilizer
        is_fert = any(w in query_lower for w in ["fertilizer", "urea", "dap", "potash", "dosage", "dose", "how much fertilizer", "ఎరువు", "ఎరువులు", "డోస్", "खाद", "उर्वरक"])

        # Assign Intent & Topic with Strict Live Tool Separation
        if is_spray_weather:
            intent = "SPRAY_WEATHER_SAFETY"
            topic = "spray_safety"
            is_live_query = True
            requires_rag = True  # Requires weather API + RAG spray safety rules
        elif is_weather and not (extracted_crop or extracted_symptoms):
            intent = "WEATHER_QUERY"
            topic = "weather"
            is_live_query = True
            requires_rag = False  # Pure live weather query
        elif is_market and not is_sell_decision and not is_profit:
            intent = "MARKET_QUERY"
            topic = "market"
            is_live_query = True
            requires_rag = False  # Pure live market query
        elif is_sell_decision:
            intent = "SELL_DECISION"
            topic = "market_decisions"
            is_live_query = True
            requires_rag = True  # Live market + RAG cold storage/warehousing
        elif is_profit:
            intent = "PROFIT_SIMULATION"
            topic = "economics"
            is_live_query = True
            requires_rag = True  # Live market + RAG cost of cultivation / yield benchmarks
        elif is_scheme:
            intent = "GOVERNMENT_SCHEME"
            topic = "government_schemes"
            is_live_query = False
            requires_rag = True
        elif is_fert:
            intent = "FERTILIZER_QUERY"
            topic = "fertilizer_recommendation"
            is_live_query = False
            requires_rag = True
        elif is_irrig:
            intent = "IRRIGATION_QUERY"
            topic = "irrigation"
            is_live_query = False
            requires_rag = True
        elif extracted_symptoms or extracted_pest:
            intent = "CROP_SYMPTOM"
            topic = "pest_disease"
            is_live_query = False
            requires_rag = True
        elif extracted_soil:
            intent = "SOIL_QUERY"
            topic = "soil_management"
            is_live_query = False
            requires_rag = True
        elif any(w in query_lower for w in ["which crop", "recommend crop", "crop for", "ఏ పంట", "పంట సిఫార్సు", "कौन सी फसल"]):
            intent = "CROP_RECOMMENDATION"
            topic = "agronomy"
            is_live_query = False
            requires_rag = True

        # If symptom inquiry and crop not in query, use farm context crop as supporting candidate
        final_crop = extracted_crop or (context_crop if extracted_symptoms else None)

        return QueryUnderstandingResult(
            original_query=query,
            normalized_query=query_clean,
            language=lang,
            intent=intent,
            crop=final_crop,
            symptoms=extracted_symptoms,
            disease=None,
            pest=extracted_pest,
            soil=extracted_soil,
            growth_stage=None,
            topic=topic,
            location=extracted_loc,
            time_context="tomorrow_morning" if "morning" in query_lower else ("tomorrow" if "tomorrow" in query_lower else None),
            is_live_query=is_live_query,
            requires_rag=requires_rag,
            confidence=0.95 if extracted_crop or extracted_symptoms else 0.85
        )

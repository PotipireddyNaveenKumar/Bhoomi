import re
import uuid
from typing import Optional, Dict, Any, Tuple, List
from app.schemas.voice_intent import VoiceIntent, VoiceIntentType
from app.schemas.task import TaskType


class IntentNormalizationService:
    """
    Multilingual Voice & Text Intent Normalization Service.
    Maps natural language queries across English (en), Telugu (te), Hindi (hi),
    Tamil (ta), Kannada (kn), and Malayalam (ml) into canonical VoiceIntent objects.
    Ensures voice and typing share the exact same decision and action path.
    """

    CROP_ALIASES: Dict[str, str] = {
        "chilli": "Chilli", "chili": "Chilli", "mirchi": "Chilli", "మిరప": "Chilli", "మిరపకాయ": "Chilli", "మిరపతోట": "Chilli", "mirapa": "Chilli", "మిర్చి": "Chilli", "मिर्च": "Chilli",
        "tomato": "Tomato", "tamatar": "Tomato", "టమోటా": "Tomato", "టమాట": "Tomato", "టమోటో": "Tomato", "tamata": "Tomato", "tamota": "Tomato", "टमाटर": "Tomato",
        "banana": "Banana", "kela": "Banana", "అరటి": "Banana", "केला": "Banana", "வாழை": "Banana",
        "corn": "Corn", "maize": "Corn", "makka": "Corn", "మొక్కజొన్న": "Corn", "मक्का": "Corn",
        "potato": "Potato", "aloo": "Potato", "బంగాళాదుంప": "Potato", "ఆलू": "Potato",
        "rice": "Rice", "paddy": "Rice", "వరి": "Rice", "ధాన్యం": "Rice", "వరిధాన్యం": "Rice", "धान": "Rice", "चावल": "Rice", "நெல்": "Rice",
        "cotton": "Cotton", "patti": "Cotton", "పత్తి": "Cotton", "దూది": "Cotton", "कपास": "Cotton",
        "wheat": "Wheat", "gehu": "Wheat", "गेहूं": "Wheat", "గోధుమ": "Wheat",
        "onion": "Onion", "pyaz": "Onion", "प्याज": "Onion", "ఉల్లి": "Onion", "ఉల్లిపాయ": "Onion",
        "pineapple": "Pineapple", "pineapples": "Pineapple", "अनानास": "Pineapple", "అనాస": "Pineapple",
        "saffron": "Saffron", "kesar": "Saffron", "केसर": "Saffron"
    }

    TASK_TYPE_KEYWORDS: Dict[TaskType, List[str]] = {
        TaskType.IRRIGATION: [
            "water", "watering", "irrigate", "irrigation", "తడి", "నీరు", "నీళ్ళు", "పారించడం",
            "पानी", "सिंचाई", "தண்ணீர்", "பாசனம்", "ನೀರು", "ನೀರಾವರಿ", "വെള്ളം", "നന"
        ],
        TaskType.SPRAYING: [
            "spray", "spraying", "pesticide", "neem", "పురుగుమందు", "స్ప్రే", "పిచికారీ",
            "छिड़काव", "स्प्रे", "কীटनाशक", "தெளிப்பு", "ಸಿಂಪಡಣೆ", "തളിക്കൽ"
        ],
        TaskType.FERTILIZATION: [
            "fertilizer", "fertilize", "urea", "nutrient", "foliar", "ఎరువు", "ఎరువులు", "పోషకాలు",
            "खाद", "उर्वरक", "உரம்", "ಗೊಬ್ಬರ", "വളം"
        ],
        TaskType.FIELD_INSPECTION: [
            "inspect", "inspection", "scout", "scouting", "check", "examine", "పరిశీలన", "చూడటం",
            "जांच", "निरीक्षण", "ஆய்வு", "ಪರಿಶೀಲನೆ", "പരിശോധന"
        ],
        TaskType.HARVEST: [
            "harvest", "harvesting", "pick", "picking", "కోత", "కోయడం",
            "कटाई", "तोड़ाई", "அறுவடை", "ಕೊಯ್ಲು", "വിളവെടുപ്പ്"
        ],
        TaskType.WEED_MANAGEMENT: [
            "weed", "weeding", "hoeing", "కలుపు", "తీత", "निराई", "களை", "ಕಳೆ", "കള"
        ]
    }

    DELAY_NUMBER_PATTERNS = [
        (r"\b(one|1|ఒక|एक|ஒரு|ಒಂದು|ഒരു)\s*(day|days|రోజు|రోజులు|दिन|நாட்கள்|ದಿನ|ദിവസം)", 1),
        (r"\b(two|2|రెండు|दो|இரண்டு|ಎರಡು|രണ്ട്)\s*(days|day|రోజులు|రోజు|दिन|நாட்கள்|ದಿನಗಳು|ദിവസം)", 2),
        (r"\b(three|3|మూడు|तीन|மூன்று|ಮೂರು|മൂന്ന്)\s*(days|day|రోజులు|రోజు|दिन|நாட்கள்|ದಿನಗಳು|ദിവസം)", 3),
        (r"\b(four|4|నాలుగు|चार|நான்கு|ನಾಲ್ಕು|നാല്)\s*(days|day|రోజులు|రోజు|दिन|நாட்கள்|ದಿನಗಳು|ദിവസം)", 4),
        (r"\b(five|5|ఐదు|पाँच|ஐந்து|ಐದು|അഞ്ച്)\s*(days|day|రోజులు|రోజు|दिन|நாட்கள்|ದಿನಗಳು|ദിവസം)", 5),
        (r"\b(tomorrow|రేపు|कल|நாளை|ನಾಳೆ|നാളെ)", 1)
    ]

    @classmethod
    def detect_language(cls, text: str, hint: Optional[str] = None) -> str:
        """Heuristic script-based language detection with English fallback."""
        if not text:
            return hint or "en"
        for char in text:
            cp = ord(char)
            if 0x0C00 <= cp <= 0x0C7F:
                return "te"
            if 0x0900 <= cp <= 0x097F:
                return "hi"
            if 0x0B80 <= cp <= 0x0BFF:
                return "ta"
            if 0x0C80 <= cp <= 0x0CFF:
                return "kn"
            if 0x0D00 <= cp <= 0x0D7F:
                return "ml"
        # If Latin letters are present, detect as English
        if any(c.isascii() and c.isalpha() for c in text):
            return "en"
        return hint or "en"

    @classmethod
    def _clean_str(cls, text: str) -> str:
        return re.sub(r"[^\w\s\u0C00-\u0C7F\u0900-\u097F\u0B80-\u0BFF\u0C80-\u0CFF\u0D00-\u0D7F]", " ", text).strip()

    @classmethod
    def parse_intent(cls, text: str, language: Optional[str] = None, confidence: float = 1.0, trace_id: str = "") -> VoiceIntent:
        """
        Deterministically extracts canonical VoiceIntent from normalized voice or typed query.
        """
        raw = text.strip()
        detected_lang = cls.detect_language(raw, language)
        normalized = raw.lower()
        active_trace = trace_id or f"trace_{uuid.uuid4().hex[:12]}"

        # Low confidence guard: If ASR or user audio is noisy/uncertain or contains no alphanumeric tokens
        if confidence < 0.65 or not raw or not any(c.isalnum() for c in raw):
            return VoiceIntent(
                intent_type=VoiceIntentType.UNKNOWN,
                language=detected_lang,
                raw_transcript=raw,
                normalized_text=normalized,
                confidence=confidence,
                trace_id=active_trace
            )

        # 1. Check Confirmation / Affirmation
        if cls._is_confirmation(normalized):
            return VoiceIntent(
                intent_type=VoiceIntentType.TASK_CONFIRM,
                language=detected_lang,
                raw_transcript=raw,
                normalized_text=normalized,
                confidence=confidence,
                trace_id=active_trace
            )

        # 2. Check Cancellation / Negative
        if cls._is_cancellation(normalized):
            return VoiceIntent(
                intent_type=VoiceIntentType.TASK_CANCEL_ACTION,
                language=detected_lang,
                raw_transcript=raw,
                normalized_text=normalized,
                confidence=confidence,
                trace_id=active_trace
            )

        # Extract entities (Crop, TaskType, DelayDays)
        crop = cls._extract_crop(normalized)
        task_type = cls._extract_task_type(normalized)
        delay_days = cls._extract_delay_days(normalized)

        # 3. Check Task Completion
        if cls._is_task_complete(normalized):
            return VoiceIntent(
                intent_type=VoiceIntentType.TASK_COMPLETE,
                language=detected_lang,
                raw_transcript=raw,
                normalized_text=normalized,
                confidence=confidence,
                target_crop=crop,
                target_task_type=task_type,
                trace_id=active_trace
            )

        # 4. Check Task Postponement
        if cls._is_task_postpone(normalized):
            return VoiceIntent(
                intent_type=VoiceIntentType.TASK_POSTPONE,
                language=detected_lang,
                raw_transcript=raw,
                normalized_text=normalized,
                confidence=confidence,
                target_crop=crop,
                target_task_type=task_type,
                requested_delay_days=delay_days or 2,
                trace_id=active_trace
            )

        # 5. Check Task Skip
        if cls._is_task_skip(normalized):
            return VoiceIntent(
                intent_type=VoiceIntentType.TASK_SKIP,
                language=detected_lang,
                raw_transcript=raw,
                normalized_text=normalized,
                confidence=confidence,
                target_crop=crop,
                target_task_type=task_type,
                confirmation_required=True,
                trace_id=active_trace
            )

        # 5.5 Agricultural News & Policy/Market Updates
        is_news_query = any(w in normalized for w in [
            "latest agriculture news", "latest news", "agriculture news", "agri news", "farming news",
            "market updates", "news update", "news updates", "updates on", "any updates", "update on",
            "what's happening with", "what is happening with", "current updates", "crop news", "price news",
            "policy news", "subsidy news", "any news", "news",
            "వార్తలు", "వ్యవసాయ వార్తలు", "తాజా వార్తలు", "రైతు వార్తలు", "మార్కెట్ వార్తలు",
            "వార్తలేమిటి", "ఏమైనా వార్తలు", "అప్‌డేట్స్", "అప్డేట్స్", "విశేషాలు",
            "समाचार", "कृषि समाचार", "ताज़ा समाचार", "ताज़ा खबरें", "खेती की खबरें",
            "किसान समाचार", "मंडी समाचार", "खबरें", "खबर", "अपडेट"
        ])
        if is_news_query:
            return VoiceIntent(
                intent_type=VoiceIntentType.AGRICULTURAL_NEWS,
                language=detected_lang,
                raw_transcript=raw,
                normalized_text=normalized,
                target_crop=crop,
                entities={"topic": crop or "general"},
                trace_id=active_trace
            )

        # 6.0 Spray Weather Safety (weather/spray suitability)
        spray_words = [
            "spray", "spraying", "herbicide", "pesticide", "fungicide", "insecticide", "weedicide",
            "స్ప్రే", "పిచికారీ", "పురుగుమందు", "మందు",
            "छिड़काव", "स्प्रे", "কীटनाशक", "தெளிப்பு", "சிಂಪಡಣೆ", "തളിക്കൽ"
        ]
        spray_condition_words = [
            "can i", "should i", "tomorrow", "today", "morning", "weather", "safe to",
            "between", "forecast", "window", "hour", "hours", "wind", "rain", "suitability",
            "చేయవచ్చా", "చేయవచ్చ?", "చేయొచ్చా", "కొట్టవచ్చా", "కొట్టొచ్చా", "రేపు", "ఈరోజు", "ఉదయం", "వాతావరణం", "కాలం",
            "कर सकता", "करना चाहिए", "कल", "आज", "सुबह", "मौसम",
            "தெளிக்கலாமா", "சிಂಪಡಿಸಬಹುದೇ", "സ്പ്രേ ചെയ്യാമോ"
        ]
        has_spray = any(w in normalized for w in spray_words)
        has_spray_cond = any(w in normalized for w in spray_condition_words)
        if has_spray and (has_spray_cond or "spray safety" in normalized or "safe to spray" in normalized):
            return VoiceIntent(
                intent_type=VoiceIntentType.SPRAY_WEATHER_SAFETY,
                language=detected_lang,
                raw_transcript=raw,
                normalized_text=normalized,
                target_crop=crop,
                target_task_type=TaskType.SPRAYING,
                trace_id=active_trace
            )

        # 6. Environmental and Weather Queries
        if any(w in normalized for w in ["weather", "rain", "rainfall", "forecast", "temperature", "వాతావరణం", "వాతావరణ", "వర్షం", "వర్ష", "मौसम", "बारिश", "तापमान", "வானிலை", "हवामान", "കാലാവസ്ഥ"]):
            return VoiceIntent(intent_type=VoiceIntentType.WEATHER_QUERY, language=detected_lang, raw_transcript=raw, normalized_text=normalized, trace_id=active_trace)

        # 7. Irrigation Queries and Decisions
        if any(w in normalized for w in ["irrigate", "irrigation", "water today", "watering today", "should i irrigate", "need to irrigate", "water the crop", "water available", "నీరు పెట్టాలా", "తడి ఇవ్వాలా", "నీటి పారుదల", "సిరచాల", "నీరు ఇవ్వాలా", "సిరచ", "సిंचाई करनी चाहिए", "पानी देना चाहिए", "सिंचाई", "நீர்ப்பாசனம்", "நೀರಾವರಿ", "നനയ്ക്കണമോ"]):
            return VoiceIntent(intent_type=VoiceIntentType.IRRIGATION_QUERY, language=detected_lang, raw_transcript=raw, normalized_text=normalized, target_crop=crop, target_task_type=TaskType.IRRIGATION, trace_id=active_trace)

        # 8. Mandi, Market, and Sell Decisions
        if any(w in normalized for w in ["price", "market", "mandi", "modal", "sell now", "should i sell", "when to sell", "rate", "ధర", "ధరలు", "మార్కెట్", "మండి", "దర", "అమ్మ", "दाम", "मंडी", "भाव", "बेच", "விலை", "ಬೆಲೆ", "വില"]):
            return VoiceIntent(intent_type=VoiceIntentType.MARKET_QUERY, language=detected_lang, raw_transcript=raw, normalized_text=normalized, target_crop=crop, trace_id=active_trace)

        # 9. Profit and Financial Simulation
        if any(w in normalized for w in ["profit", "net profit", "revenue", "margin", "economics", "roi", "profitable", "yield decreases", "price falls", "లాభ", "లాభాల", "ఆదాయం", "मुनाफा", "आमदनी", "लाभ"]):
            return VoiceIntent(intent_type=VoiceIntentType.PROFIT_QUERY, language=detected_lang, raw_transcript=raw, normalized_text=normalized, target_crop=crop, trace_id=active_trace)

        # 10. Harvest Queries
        if any(w in normalized for w in ["harvest", "ready to harvest", "when should i harvest", "picking", "కోత", "కోయడం", "कटाई", "तोड़ाई"]):
            return VoiceIntent(intent_type=VoiceIntentType.HARVEST_QUERY, language=detected_lang, raw_transcript=raw, normalized_text=normalized, target_crop=crop, trace_id=active_trace)

        # 11. Fertilizer Inquiries
        if any(w in normalized for w in ["fertilizer", "urea", "dap", "potash", "19:19:19", "nutrient", "yellow leaves", "nitrogen deficiency", "foliar", "ఎరువు", "ఎరువులు", "खाद", "उर्वरक"]):
            return VoiceIntent(intent_type=VoiceIntentType.FERTILIZER_QUERY, language=detected_lang, raw_transcript=raw, normalized_text=normalized, target_crop=crop, trace_id=active_trace)

        # 12. Pest and Disease Queries
        pest_keywords = [
            "curling", "curl", "curled", "spots", "leaf curl", "blight", "pests", "insects",
            "insecticide", "fungicide", "infestation", "yellow mosaic", "wilt", "rot", "damping off",
            "whitefly", "thrips", "aphids", "mites", "caterpillar", "borer",
            "ముడుచు", "ముడత", "ముడుచుకుంటున్నాయి", "ముడుచుకుంటుంది", "ఆకు ముడత", "ఆకులు ముడుచు", "ఆకులు",
            "తెగులు", "పురుగు", "కీటకాలు", "నల్లి", "తామర", "దోమ", "మచ్చలు", "కుళ్లు",
            "बीमारी", "कीट", "मरोड़िया", "सिकुड़", "सिकुड़ना", "पत्ती मुड़", "पत्तियां मुड़", "पत्तियाँ मुड़", "पत्तियां मुड़", "पत्तियाँ मुड़", "मुड़ रही", "मुड़ रही", "मुड़", "मुड़", "मुड़ना", "मुड़ना", "धब्बे", "सड़न",
            "சுருட்டை", "இலை சுருட்டை", "நோய்", "பூச்சி",
            "ಮುದುಡುವಿಕೆ", "ಎಲೆ ಮುದುಡುವುದು", "ರೋಗ", "ಕೀಟ",
            "ചുരുളൽ", "ഇല ചുരുളൽ", "രോഗം", "കീടം"
        ]
        if any(w in normalized for w in pest_keywords):
            return VoiceIntent(intent_type=VoiceIntentType.PEST_QUERY, language=detected_lang, raw_transcript=raw, normalized_text=normalized, target_crop=crop, trace_id=active_trace)

        # 13. Crop Recommendation & Selection
        if any(w in normalized for w in ["which crop", "recommend crop", "crop recommendation", "best crop", "crop for black soil", "suitable for black soil", "grow a crop", "want to grow", "crop selection", "ఏ పంట వేయాలి", "ఏ పంట మంచిది", "నల్లరేగడి", "నల్ల రేగడి", "పంట సిఫార్సు", "कौन सी फसल", "काली मिट्टी", "फसल लगाना"]):
            return VoiceIntent(intent_type=VoiceIntentType.CROP_RECOMMENDATION, language=detected_lang, raw_transcript=raw, normalized_text=normalized, target_crop=crop, trace_id=active_trace)

        # 14. Crop Management & Stage
        if any(w in normalized for w in ["planted", "crop stage", "what stage", "what should i do now", "management", "పంట దశ", "నాటిన తర్వాత"]):
            return VoiceIntent(intent_type=VoiceIntentType.CROP_MANAGEMENT, language=detected_lang, raw_transcript=raw, normalized_text=normalized, target_crop=crop, trace_id=active_trace)

        # 15. Farm Changes and What is New
        if any(w in normalized for w in ["what changed", "what is new", "what's new", "recent changes", "మార్పులు", "ఏమి మారాయి", "क्या बदला", "क्या नया है"]):
            return VoiceIntent(intent_type=VoiceIntentType.FARM_CHANGES, language=detected_lang, raw_transcript=raw, normalized_text=normalized, trace_id=active_trace)

        # 16. Farm Status / Crop Health Status
        if any(w in normalized for w in ["how is my crop", "how is my farm", "crop health", "farm health", "status of my farm", "నా పంట ఎలా ఉంది", "పంట పరిస్థితి"]):
            return VoiceIntent(intent_type=VoiceIntentType.CROP_STATUS, language=detected_lang, raw_transcript=raw, normalized_text=normalized, target_crop=crop, trace_id=active_trace)

        # 17. Why / Reason Queries (Specifically for Farm Tasks & Postponements)
        task_why_markers = [
            "why should i", "why was", "why postpone", "why is this task", "why is this due", "why delay",
            "why irrigate", "why water", "why spray", "why fertilize",
            "వాయిదా ఎందుకు", "ఈ పని ఎందుకు", "ఎందుకు వాయిదా", "ఎందుకు నీరు పెట్టాలి", "ఎందుకు స్ప్రే చేయాలి",
            "పని ఎందుకు", "డ్యూ ఎందుకు", "టాస్క్ ఎందుకు",
            "क्यों टालें", "यह काम क्यों", "काम क्यों", "सिंचाई क्यों", "स्थगित क्यों"
        ]
        has_foliar_symptom = any(w in normalized for w in [
            "curl", "curling", "spots", "blight", "yellow", "ముడుచు", "ముడత", "నల్లి", "తామర", "పురుగు", "తెగులు", "మచ్చలు", "పసుపు",
            "पत्ती मुड़", "पत्तियां मुड़", "मरोड़", "रोग", "धब्बे", "पीली", "झुलसा"
        ])
        is_task_why = (
            not has_foliar_symptom and (
                any(w in normalized for w in task_why_markers)
                or (("why" in normalized or "ఎందుకు" in normalized or "क्यों" in normalized) and (task_type is not None or any(w in normalized for w in ["task", "postpone", "delay", "due", "పని", "వాయిదా", "काम"])))
            )
        )
        if is_task_why:
            return VoiceIntent(
                intent_type=VoiceIntentType.TASK_WHY,
                language=detected_lang,
                raw_transcript=raw,
                normalized_text=normalized,
                target_crop=crop,
                target_task_type=task_type,
                trace_id=active_trace
            )

        # 18. Weekly Task Queries
        if any(w in normalized for w in ["what should i do this week", "weekly plan", "weekly tasks", "this week", "ఈ వారం", "ఈ వారపు పనులు", "इस हफ्ते", "इस सप्ताह", "இந்த வாரம்", "ಈ ವಾರ", "ഈ ആഴ്ച"]):
            return VoiceIntent(intent_type=VoiceIntentType.TASK_WEEK, language=detected_lang, raw_transcript=raw, normalized_text=normalized, trace_id=active_trace)

        # 19. Pending and Overdue Tasks
        if any(w in normalized for w in ["what is pending", "what did i miss", "what is overdue", "what should i do next", "pending tasks", "బాకీ పనులు", "మిగిలిన పనులు", "बाकी काम", "बकाया काम"]):
            return VoiceIntent(intent_type=VoiceIntentType.TASK_PENDING, language=detected_lang, raw_transcript=raw, normalized_text=normalized, trace_id=active_trace)

        # 20. Today Specific Farm Manager Priorities and Tasks
        is_bare_today = normalized.strip() in ["today", "ఈరోజు", "आज", "இன்று", "ಇಂದು", "ഇന്ന്"]
        is_task_today = (
            is_bare_today
            or any(w in normalized for w in ["what should i do today", "what to do today", "today's task", "today's tasks", "tasks for today"])
            or ("today" in normalized and any(w in normalized for w in ["task", "tasks", "priority", "priorities", "schedule", "work", "do", "action"]))
            or ("ఈరోజు" in normalized and any(w in normalized for w in ["ఏం చేయాలి", "ఏమి చేయాలి", "పనులు", "చేయాలి", "పని"]))
            or ("నేను ఏమి చేయాలి" in normalized)
            or ("आज" in normalized and any(w in normalized for w in ["क्या करना", "क्या करें", "काम", "कार्य", "करना चाहिए", "करना"]))
            or ("இன்று" in normalized and any(w in normalized for w in ["என்ன செய்ய", "பணிகள்", "வேலை"]))
            or ("ಇಂದು" in normalized and any(w in normalized for w in ["ಏನು ಮಾಡ", "ಕೆಲಸ"]))
            or ("ഇന്ന്" in normalized and any(w in normalized for w in ["എന്ത് ചെയ്യ", "ജോലി"]))
        )
        if is_task_today:
            return VoiceIntent(intent_type=VoiceIntentType.TASK_TODAY, language=detected_lang, raw_transcript=raw, normalized_text=normalized, trace_id=active_trace)

        # 21. General Greetings (short utterances)
        if any(w in normalized for w in ["hello", "hi", "hey", "namaste", "namaskaram", "నమస్కారం", "నమస్తే", "హలో", "नमस्ते", "வணக்கம்", "நமஸ்காரம்", "ನಮಸ್ಕಾರ", "നമസ്കാരം"]) and len(normalized.split()) <= 4:
            return VoiceIntent(intent_type=VoiceIntentType.GENERAL_GREETING, language=detected_lang, raw_transcript=raw, normalized_text=normalized, trace_id=active_trace)

        # Default: General Agriculture
        return VoiceIntent(
            intent_type=VoiceIntentType.GENERAL_AGRICULTURE,
            language=detected_lang,
            raw_transcript=raw,
            normalized_text=normalized,
            target_crop=crop,
            target_task_type=task_type,
            trace_id=active_trace
        )

    @classmethod
    def _is_confirmation(cls, text: str) -> bool:
        cleaned = cls._clean_str(text)
        tokens = cleaned.split()
        if not tokens:
            return False
        # Do not treat as bare confirmation if action keywords are present
        if any(w in cleaned for w in ["postpone", "delay", "skip", "water", "irrigate", "spray", "finish", "complete", "వాయిదా", "దాటవేయి", "స్థगित", "टाल"]):
            return False
        affirmatives = [
            "yes", "confirm", "proceed", "ok", "okay", "sure", "correct", "yep", "do it",
            "అవును", "సరే", "చెయ్యి", "ఖరారు", "ఖచ్చితంగా",
            "हाँ", "हा", "सही", "कर दो", "ठीक है", "बिल्कुल",
            "ஆம்", "சரி", "செய்", "கண்டிப்பாக",
            "ಹೌದು", "ಸರಿ", "ಮಾಡು",
            "അതെ", "ശരി", "ചെയ്യുക"
        ]
        return cleaned in affirmatives or (len(tokens) <= 2 and any(t in affirmatives for t in tokens))

    @classmethod
    def _is_cancellation(cls, text: str) -> bool:
        cleaned = cls._clean_str(text)
        tokens = cleaned.split()
        if not tokens:
            return False
        if any(w in cleaned for w in ["postpone", "delay", "skip", "వాయిదా", "దాటవేయి", "స్థगित"]):
            return False
        negatives = [
            "no", "cancel", "abort", "don't", "stop", "nevermind", "nah",
            "వద్దు", "రద్దు", "ఆపు", "చేయవద్దు",
            "नहीं", "ना", "रद्द", "रोको", "मत करो",
            "இல்லை", "வேண்டாம்", "ரத்து",
            "ಬೇಡ", "ಇಲ್ಲ", "ರದ್ದು",
            "വേണ്ട", "അല്ല", "റദ്ദാക്കുക"
        ]
        return cleaned in negatives or (len(tokens) <= 2 and any(t in negatives for t in tokens))

    @classmethod
    def _is_task_complete(cls, text: str) -> bool:
        cleaned = cls._clean_str(text)
        indicators = [
            "finished", "completed", "done with", "already done", "completed the",
            "i watered", "i sprayed", "i harvested", "i checked", "done watering",
            "పూర్తి చేశాను", "పూర్తయింది", "పూర్తయినది", "చేశాను", "నీరు పెట్టడం పూర్తి",
            "నీరు పెట్టాను", "స్ప్రే చేశాను", "కోత కోశాను", "పరిశీలించాను",
            "पूरा कर लिया", "पूरा हो गया", "खत्म हो गया", "पानी दे दिया", "छिड़काव कर दिया", "काट लिया",
            "पूरी कर ली", "पूरी हो गई", "सिंचाई पूरी", "पानी लगा दिया", "हो गया",
            "ముடித்துவிட்டேன்", "முடிந்தது", "செய்துவிட்டேன்",
            "ಮುಗಿಸಿದೆ", "ಪೂರ್ಣಗೊಂಡಿದೆ", "ಮಾಡಿದ್ದೇನೆ",
            "പൂർത്തിയാക്കി", "കഴിഞ്ഞು", "ചെയ്തു"
        ]
        return any(ind in cleaned for ind in indicators)

    @classmethod
    def _is_task_postpone(cls, text: str) -> bool:
        cleaned = cls._clean_str(text)
        indicators = [
            "postpone", "delay", "move to", "push to", "reschedule", "later",
            "వాయిదా", "ఆలస్యం", "తర్వాత", "తరవాత",
            "स्थगित", "टाल दो", "बाद में", "कल करेंगे", "आगे बढ़ाओ",
            "ஒத்திவை", "தாமதப்படுத்து", "பிறகு",
            "ಮುಂದೂಡು", "ನಂತರ",
            "മാറ്റിവെക്കുക", "പിന്നീട്"
        ]
        return any(ind in cleaned for ind in indicators)

    @classmethod
    def _is_task_skip(cls, text: str) -> bool:
        cleaned = cls._clean_str(text)
        indicators = [
            "skip", "don't want to do", "leave it", "cancel this task", "skip today",
            "దాటవేయి", "వద్దు ఈ పని", "చేయను", "స్కిప్",
            "छोड़ दो", "नहीं करना", "स्किप", "रद्द करो",
            "தவிர்", "வேண்டாம்",
            "ಬಿಟ್ಟುಬಿಡು", "ಮಾಡಲ್ಲ",
            "ഒഴിവാക്കുക", "വേണ്ട"
        ]
        return any(ind in cleaned for ind in indicators)

    @classmethod
    def _extract_crop(cls, text: str) -> Optional[str]:
        cleaned = cls._clean_str(text)
        sorted_aliases = sorted(cls.CROP_ALIASES.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            canon = cls.CROP_ALIASES[alias]
            if alias.isascii() and alias.isalnum():
                if re.search(r"\b" + re.escape(alias) + r"\b", cleaned, re.IGNORECASE):
                    return canon
            elif alias in cleaned:
                return canon
        return None

    @classmethod
    def _extract_task_type(cls, text: str) -> Optional[TaskType]:
        cleaned = cls._clean_str(text)
        for ttype, kw_list in cls.TASK_TYPE_KEYWORDS.items():
            if any(kw in cleaned for kw in kw_list):
                return ttype
        return None

    @classmethod
    def _extract_delay_days(cls, text: str) -> Optional[int]:
        cleaned = cls._clean_str(text)
        for pattern, days in cls.DELAY_NUMBER_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                return days
        # Fallback digits extraction
        m = re.search(r"(\d+)\s*(days|day|రోజులు|दिन)", cleaned)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        return None

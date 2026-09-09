from typing import Optional, List, Dict, Any, Tuple


class MissingInfoResult(str):
    def __new__(cls, text: str, slot: str = ""):
        obj = str.__new__(cls, text)
        obj.slot = slot
        return obj

    def __iter__(self):
        return iter((str(self), self.slot))


class MissingInformationDetector:
    """
    Detects underspecified agricultural queries and formulates targeted, proactive
    single-question clarifications following conversational turn-taking principles.
    Never overwhelms the farmer with multi-part questions at once.
    """

    LOCALIZED_QUESTIONS = {
        "ask_soil_for_crop": {
            "en": "Sure. I can help you choose a suitable crop. What type of soil do you have?",
            "te": "ఖచ్చితంగా. మీ పొలానికి అనువైన పంటను ఎంచుకోవడానికి నేను సహాయపడతాను. మీ నేల ఏ రకం?",
            "hi": "ज़रूर। मैं आपकी ज़मीन के लिए सही फसल चुनने में मदद कर सकता हूँ। आपकी मिट्टी किस प्रकार की है?",
            "ta": "நிச்சயமாக. உங்கள் பண்ணைக்கு ஏற்ற பயிரைத் தேர்ந்தெடுக்க நான் உதவுகிறேன். உங்கள் மண் என்ன வகை?",
            "kn": "ಖಂಡಿತವಾಗಿಯೂ. ನಿಮ್ಮ ಜಮೀನಿಗೆ ಸೂಕ್ತವಾದ ಬೆಳೆಯನ್ನು ಆಯ್ಕೆ ಮಾಡಲು ನಾನು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ. ನಿಮ್ಮ ಮಣ್ಣು ಯಾವ ಪ್ರಕಾರದ್ದು?",
            "ml": "തീർച്ചയായും. നിങ്ങളുടെ കൃഷിയിടത്തിന് അനുയോജ്യമായ വിള തിരഞ്ഞെടുക്കാൻ ഞാൻ സഹായിക്കാം. നിങ്ങളുടെ മണ്ണ് ഏത് തരത്തിലുള്ളതാണ്?"
        },
        "ask_irrigation_for_crop": {
            "en": "How much water is available for irrigation?",
            "te": "నీటిపారుదలకి ఎంత నీరు అందుబాటులో ఉంది?",
            "hi": "सिंचाई के लिए कितना पानी उपलब्ध है?",
            "ta": "நீர்ப்பாசனத்திற்கு எவ்வளவு தண்ணீர் வசதி உள்ளது?",
            "kn": "ನೀರಾವರಿಗೆ ಎಷ್ಟು ನೀರು ಲಭ್ಯವಿದೆ?",
            "ml": "നനയ്ക്കാൻ എത്രത്തോളം വെള്ളം ലഭ്യമാണ്?"
        },
        "confirm_crop_recommendation": {
            "en": "Based on your soil and irrigation availability, I can compare suitable crops. Would you like me to recommend them?",
            "te": "మీ నేల రకం మరియు నీటి లభ్యత ఆధారంగా అనువైన పంటలను సరిపోల్చగలను. వాటిని సిఫార్సు చేయమంటారా?",
            "hi": "आपकी मिट्टी और सिंचाई की उपलब्धता के आधार पर मैं उपयुक्त फसलों की तुलना कर सकता हूँ। क्या मैं सिफारिश प्रस्तुत करूँ?",
            "ta": "உங்கள் மண் மற்றும் நீர் வசதியின் அடிப்படையில் ஏற்ற பயிர்களை ஒப்பிட முடியும். பரிந்துரைக்கவா?",
            "kn": "ನಿಮ್ಮ ಮಣ್ಣು ಮತ್ತು ನೀರಾವರಿ ಲಭ್ಯತೆಯ ಆಧಾರದ ಮೇಲೆ ಸೂಕ್ತ ಬೆಳೆಗಳನ್ನು ಶಿಫಾರಸು ಮಾಡಲೇ?",
            "ml": "നിങ്ങളുടെ മണ്ണും ജലലഭ്യതയും അനുസരിച്ച് അനുയോജ്യമായ വിളകൾ താരതമ്യം ചെയ്യാം. ശുപാർശ നൽകണമെന്നുണ്ടോ?"
        },
        "ask_crop_for_fertilizer": {
            "en": "Which crop are you growing, and what is its current growth stage?",
            "te": "మీరు ఏ పంటకు ఎరువులు వేయాలనుకుంటున్నారు, మరియు ప్రస్తుతం పంట ఏ దశలో ఉంది?",
            "hi": "आप किस फसल के लिए खाद डालना चाहते हैं, और फसल की वर्तमान अवस्था क्या है?",
            "ta": "நீங்கள் எந்தப் பயிருக்கு உரம் இட திட்டமிட்டுள்ளீர்கள், அதன் வளர்ச்சி நிலை என்ன?",
            "kn": "ನೀವು ಯಾವ ಬೆಳೆಗೆ ಗೊಬ್ಬರ ಹಾಕಲು ಯೋಜಿಸುತ್ತಿದ್ದೀರಿ ಮತ್ತು ಬೆಳೆಯ ಪ್ರಸ್ತುತ ಹಂತವೇನು?",
            "ml": "ഏത് വിളയ്ക്കാണ് വളപ്രയോഗം നടത്താൻ ഉദ്ദേശിക്കുന്നത്, വിളയുടെ ഇപ്പോഴത്തെ വളർച്ചാ ഘട്ടം എന്താണ്?"
        },
        "ask_symptoms_for_pest": {
            "en": "Could you describe the symptoms? For example, are leaves curling upwards, yellowing, or showing spots? A clear photo will also help.",
            "te": "లక్షణాలు ఎలా ఉన్నాయో వివరించగలరా? ఉదాహరణకు, ఆకులు పైకి ముడుచుకుంటున్నాయా, పసుపు రంగులోకి మారుతున్నాయా, లేదా మచ్చలున్నాయా? స్పష్టమైన ఫోటో తీసి పంపితే మరింత సహాయపడుతుంది.",
            "hi": "क्या आप लक्षणों का विवरण दे सकते हैं? जैसे क्या पत्तियाँ ऊपर की ओर मुड़ रही हैं, पीली पड़ रही हैं या धब्बे हैं? एक स्पष्ट फोटो भी भेज सकते हैं।",
            "ta": "அறிகுறிகளை விவரிக்க முடியுமா? எடுத்துக்காட்டாக, இலைகள் மேல்நோக்கி சுருளுகிறதா, மஞ்சளாகிறதா, அல்லது புள்ளிகள் உள்ளதா?",
            "kn": "ರೋಗಲಕ್ಷಣಗಳನ್ನು ವಿವರಿಸಬಹುದೇ? ಉದಾಹರಣೆಗೆ, ಎಲೆಗಳು ಮೇಲಕ್ಕೆ ಮುದುಡಿಕೊಳ್ಳುತ್ತಿವೆಯೇ, ಹಳದಿಯಾಗುತ್ತಿವೆಯೇ ಅಥವಾ ಕಲೆಗಳಿವೆಯೇ?",
            "ml": "ലക്ഷണങ്ങൾ വിവരിക്കാമോ? ഉദാഹരണത്തിന് ഇലകൾ മുകളിലേക്ക് ചുരുളുന്നുണ്ടോ, മഞ്ഞനിറമാകുന്നുണ്ടോ അതോ പാടുകൾ ഉണ്ടോ?"
        }
    }

    @classmethod
    def get_localized_question(cls, key: str, language: str = "en") -> str:
        lang_dict = cls.LOCALIZED_QUESTIONS.get(key, {})
        return lang_dict.get(language, lang_dict.get("en", ""))

    @classmethod
    def check_missing_info(
        cls,
        user_text: str,
        context_memories: Dict[str, str],
        active_crops: List[Dict[str, Any]],
        collected_slots: Optional[Dict[str, Any]] = None,
        language: str = "en"
    ) -> Optional[Tuple[str, str]]:
        """
        Returns (question_text, pending_slot_name) if information is missing, or None.
        """
        text_lower = user_text.lower()
        slots = collected_slots or {}

        # 1. Crop Selection / Planning Intent
        is_crop_planning = any(term in text_lower for term in [
            "grow a crop", "want to grow", "want to plant", "choose a crop", "which crop should i grow",
            "which crop to grow", "recommend a crop", "recommend crop", "crop recommendation",
            "పంట వేద్దామనుకుంటున్నాను", "ఏ పంట వేయాలి", "ఏ పంట మంచిది", "పంట సిఫార్సు",
            "फसल लगाना चाहता हूँ", "कौन सी फसल लगाएं", "फसल सिफारिश",
            "பயிர் நட விரும்புகிறேன்", "எந்த பயிர் நடலாம்",
            "ಬೆಳೆ ಬೆಳೆಯಲು ಬಯಸುತ್ತೇನೆ", "ಯಾವ ಬೆಳೆ ಬೆಳೆಯಬೇಕು",
            "വിള കൃഷി ചെയ്യാൻ ആഗ്രഹിക്കുന്നു", "ഏത് വിള കൃഷി ചെയ്യണം"
        ])

        if is_crop_planning:
            has_soil = bool(slots.get("soil_type")) or ("soil_type" in context_memories) or any(
                s in text_lower for s in ["black", "red", "alluvial", "sandy", "clay", "loamy", "నల్లరేగడి", "काली", "கரிசல்", "ಕಪ್ಪು", "കറുത്ത"]
            )
            has_irrigation = bool(slots.get("irrigation_water")) or ("irrigation_source" in context_memories) or any(
                w in text_lower for w in ["borewell", "canal", "drip", "rainfed", "good irrigation", "water available", "బావి", "బోరు", "కాలువ", "पानी", "सिंचाई"]
            )

            if not has_soil:
                return MissingInfoResult(cls.get_localized_question("ask_soil_for_crop", language), "SOIL_TYPE")
            if not has_irrigation:
                return MissingInfoResult(cls.get_localized_question("ask_irrigation_for_crop", language), "IRRIGATION_AVAILABILITY")
            # Both slots present, prompt recommendation confirmation
            return MissingInfoResult(cls.get_localized_question("confirm_crop_recommendation", language), "CONFIRM_CROP_RECOMMENDATION")

        # 2. Fertilizer inquiry without known crop
        if any(term in text_lower for term in ["fertilizer", "urea", "dap", "potash", "ఎరువు", "खाद", "உரம்", "ಗೊಬ್ಬರ", "വളം"]):
            has_crop = bool(active_crops) or ("crop" in context_memories) or any(
                c in text_lower for c in ["chilli", "cotton", "rice", "paddy", "maize", "tomato", "banana", "mirchi", "వరి", "మిర్చి", "मिर्च", "धान"]
            )
            if not has_crop:
                return MissingInfoResult(cls.get_localized_question("ask_crop_for_fertilizer", language), "TARGET_CROP")

        # 3. Sick crop / pest inquiry without symptoms
        if text_lower.strip() in [
            "my crop is sick", "crop is sick", "crop sick", "leaves are damaged",
            "నా పంటకు రోగం వచ్చింది", "నా పంట బాగాలేదు", "मेरी फसल बीमार है", "फसल खराब हो रही है",
            "என் பயிர் நோய்வாய்ப்பட்டுள்ளது", "ನನ್ನ ಬೆಳೆ ಅನಾರೋಗ್ಯಕ್ಕೊಳಗಾಗಿದೆ", "എന്റെ വിളയ്ക്ക് അസുഖമാണ്"
        ]:
            return MissingInfoResult(cls.get_localized_question("ask_symptoms_for_pest", language), "PEST_SYMPTOMS")

        return None

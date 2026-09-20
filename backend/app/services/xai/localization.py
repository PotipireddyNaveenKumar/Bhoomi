from typing import Dict, Any, List, Optional
from app.services.voice.persona import BhoomiPersonaEngine


class XAILocalizationService:
    """
    Multilingual Explainable AI formatting engine supporting all 6 authoritative locales:
    en, te, hi, ta, kn, ml.
    Standardizes numeric terms while presenting surrounding narrative in the selected locale.
    """

    LABELS: Dict[str, Dict[str, str]] = {
        "why": {
            "en": "WHY",
            "te": "ఎందుకు (కారణం)",
            "hi": "कारण (क्यों)",
            "ta": "ஏன் (காரணம்)",
            "kn": "ಏಕೆ (ಕಾರಣ)",
            "ml": "എന്തുകൊണ്ട് (കാരണം)"
        },
        "evidence": {
            "en": "EVIDENCE",
            "te": "ఆధారాలు (పరిశోధనా సమాచారం)",
            "hi": "प्रमाण (अनुसंधान साक्ष्य)",
            "ta": "ஆதாரம் (ஆராய்ச்சி தகவல்)",
            "kn": "ಸಾಕ್ಷ್ಯಾಧಾರ (ಸಂಶೋಧನಾ ಮಾಹಿತಿ)",
            "ml": "തെളിവ് (ഗവേഷണ രേഖകൾ)"
        },
        "current_data": {
            "en": "CURRENT DATA",
            "te": "ప్రస్తుత సమాచారం",
            "hi": "वर्तमान डेटा",
            "ta": "தற்போதைய தரவு",
            "kn": "ಪ್ರಸ್ತುತ ಮಾಹಿತಿ",
            "ml": "നിലവിലെ വിവരങ്ങൾ"
        },
        "limitations": {
            "en": "LIMITATIONS",
            "te": "పరిమితులు",
            "hi": "सीमाएं / ध्यान देने योग्य बातें",
            "ta": "வரம்புகள்",
            "kn": "ಮಿತಿಗಳು",
            "ml": "പരിമിതികൾ"
        },
        "weather": {
            "en": "Weather",
            "te": "వాతావరణం",
            "hi": "मौसम",
            "ta": "வானிலை",
            "kn": "ಹವಾಮಾನ",
            "ml": "കാലാവസ്ഥ"
        },
        "market": {
            "en": "Market",
            "te": "మార్కెట్ ధరలు",
            "hi": "मंडी भाव",
            "ta": "சந்தை நிலவரம்",
            "kn": "ಮಾರುಕಟ್ಟೆ ದರ",
            "ml": "വിപണി നിരക്ക്"
        },
        "insufficient_evidence": {
            "en": "Verified agricultural research evidence was insufficient for this specific scenario.",
            "te": "ఈ నిర్దిష్ట పంట పరిస్థితికి ధృవీకరించబడిన పరిశోధనా ఆధారాలు తగినంతగా లేవు.",
            "hi": "इस विशिष्ट स्थिति के लिए सत्यापित कृषि अनुसंधान साक्ष्य अपर्याप्त थे।",
            "ta": "இந்த குறிப்பிட்ட சூழ்நிலைக்கு சரிபார்க்கப்பட்ட வேளாண் ஆராய்ச்சி ஆதாரங்கள் போதுமானதாக இல்லை.",
            "kn": "ಈ ನಿರ್ದಿಷ್ಟ ಸನ್ನಿವೇಶಕ್ಕೆ ಪರಿಶೀಲಿಸಿದ ಕೃಷಿ ಸಂಶೋಧನಾ ಪುರಾವೆಗಳು ಸಾಕಷ್ಟಿಲ್ಲ.",
            "ml": "ഈ നിർദ്ദിഷ്ട സാഹചര്യത്തിന് പരിശോധിച്ചുറപ്പിച്ച കാർഷിക ഗവേഷണ തെളിവുകൾ അപര്യാപ്തമാണ്."
        },
        "unavailable_data": {
            "en": "Data currently unavailable from provider.",
            "te": "ప్రొవైడర్ నుండి సమాచారం ప్రస్తుతం అందుబాటులో లేదు.",
            "hi": "प्रदाता से वर्तमान डेटा उपलब्ध नहीं है।",
            "ta": "வழங்குநரிடமிருந்து தகவல் தற்போது கிடைக்கவில்லை.",
            "kn": "ಪೂರೈಕೆದಾರರಿಂದ ಮಾಹಿತಿ ಪ್ರಸ್ತುತ ಲಭ್ಯವಿಲ್ಲ.",
            "ml": "ദാതാവിൽ നിന്നുള്ള വിവരങ്ങൾ നിലവിൽ ലഭ്യമല്ല."
        }
    }

    @classmethod
    def get_label(cls, key: str, lang: str = "en") -> str:
        active = lang if lang in cls.LABELS.get(key, {}) else "en"
        return cls.LABELS.get(key, {}).get(active, cls.LABELS.get(key, {}).get("en", key))

    @classmethod
    def format_farmer_explanation(
        cls,
        why_bullets: List[str],
        evidence_bullets: List[str],
        weather_status: str,
        market_status: str,
        limitations: List[str],
        lang: str = "en"
    ) -> str:
        """
        Formats structured farmer-facing explanation string in the selected locale:
        WHY: ...
        EVIDENCE: ...
        CURRENT DATA: ...
        LIMITATIONS: ...
        """
        l_why = cls.get_label("why", lang)
        l_ev = cls.get_label("evidence", lang)
        l_data = cls.get_label("current_data", lang)
        l_lim = cls.get_label("limitations", lang)
        l_w = cls.get_label("weather", lang)
        l_m = cls.get_label("market", lang)

        parts = []

        # 1. WHY
        parts.append(f"{l_why}:")
        if why_bullets:
            for b in why_bullets:
                parts.append(f"- {b}")
        else:
            parts.append("- Agronomic guidance profile match.")

        # 2. EVIDENCE
        parts.append(f"\n{l_ev}:")
        if evidence_bullets:
            for b in evidence_bullets:
                parts.append(f"- {b}")
        else:
            parts.append(f"- {cls.get_label('insufficient_evidence', lang)}")

        # 3. CURRENT DATA
        parts.append(f"\n{l_data}:")
        parts.append(f"- {l_w}: {weather_status}")
        parts.append(f"- {l_m}: {market_status}")

        # 4. LIMITATIONS
        if limitations:
            parts.append(f"\n{l_lim}:")
            for b in limitations:
                parts.append(f"- {b}")

        return "\n".join(parts)

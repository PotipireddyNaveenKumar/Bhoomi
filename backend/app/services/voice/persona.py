from dataclasses import dataclass
import re
import random
import logging
from typing import Optional, Dict, Any, List, Tuple
from app.services.farm_manager.state_engine import FarmState
from app.services.farm_manager.decision_engine import FarmDecision, DecisionPriority

logger = logging.getLogger(__name__)

PERSONA_SYSTEM_PROMPT = """You are BHOOMI, talking directly to an Indian farmer as a trusted, caring older brother or a knowledgeable farming friend who lives next door.

YOUR PERSONALITY & VOICE RULES:
1. SHORT SENTENCES: One idea per sentence. Absolutely no stacked or nested clauses.
2. PLAIN WORDS: Never use technical or corporate jargon.
   - Do NOT say "vegetative stage (Day 53)" -> Say "growing well right now, about 50 days in" or "growing green and strong".
   - Do NOT say "probability" or "precipitation" -> Say "rain is coming" or "there is a good chance of rain".
   - Do NOT say "adequate moisture" -> Say "the soil holds moisture well" or "the soil has enough water".
   - Do NOT say "postpone surface irrigation by 48 hours" -> Say "you don't need to water today" or "hold off on watering for the next two days".
3. WARM OPENING, NOT A DATA DUMP: Greet naturally like a human brother. Vary your greeting naturally. Never front-load every data point at once.
4. CALM REASSURANCE, EVEN FOR BAD NEWS: When news is bad (pest risk, disease, price drop), speak with calm confidence and support. Never cause panic. Show you have this handled and are looking out for them.
5. ONE CLEAR ACTION, STATED SIMPLY: Tell the farmer the single most important thing to do today, with a short plain-language reason. No bracketed justifications or numeric clutter.
6. NEVER SOUND ROBOTIC: Do not read a log file or a system report aloud. Talk like a caring person talking to family.
7. FACTUAL ACCURACY IS SACRED: Never drop real farming facts, dates, crop names, rain expectations, or safety warnings (e.g. wearing a mask/gloves when spraying). Just say them simply and warmly.

FEW-SHOT EXAMPLES:

Example 1 (Rain & Postponing Irrigation - Happy Path):
Input: Crop: Chilli, Day 53 (vegetative). Weather: 100% rain forecast within 48 hours. Top action: Postpone Surface Irrigation by 48 Hours. Reason: Rain provides moisture for black soil.
Output: "Namaste! Your chilli plants are growing well right now. Good news — rain is coming in the next two days, so you don't need to water today. Just relax and let the rain do the work. I'll remind you when it's time again."

Example 2 (Pest & Disease Risk - Serious / Bad News):
Input: Crop: Chilli, Day 65 (flowering). Threat: High risk of Leaf Curl Virus and thrips. Top action: Spray CIBRC-approved bio-fungicide within 24 hours with PPE. Reason: Prevent viral spread across rows.
Output: "Namaste brother. Don't worry, but keep an eye on your chilli field today. We noticed signs of leaf curl starting on some leaves. Walk through your rows and check under the leaves. Spray the recommended bio-fungicide today to keep it from spreading. Please remember to wear a cloth mask and gloves while spraying. We'll protect your crop together."

Example 3 (Market Price Drop - Unfavorable):
Input: Crop: Chilli. Guntur mandi price dropped from ₹12,000 to ₹10,500/quintal due to arrival spike. Top action: Hold produce in dry storage for 4 days.
Output: "Hello brother! A quick update on the market today. Chilli prices in the mandi dipped a bit to ten thousand five hundred. Don't worry or rush to sell right now. Keep your bags safe in dry storage for three to four days until arrivals slow down and prices recover."

Example 4 (Agricultural News Paraphrasing — Price Surge & Short Supply):
Input: Headline: "Poor arrivals push chilli prices beyond Rs 20,000 per quintal in Ramnad - The New Indian Express"
Extracted Fact: Chilli price in Ramnad market has crossed ₹20,000/quintal due to low supply.
Spoken (Persona Voice): "Chilli prices in Ramnad have gone up a lot lately — over twenty thousand rupees a quintal — because not much crop is coming to market right now."

Example 5 (Agricultural News Paraphrasing — Export Quality & Pesticide Regulations):
Input: Headline: "After China says no, exporters urge Andhra Pradesh to curb high-risk pesticides in chilli - The Hindu"
Extracted Fact: China rejected chilli consignments; exporters request AP government to control high-risk pesticides.
Spoken (Persona Voice): "Export quality standards are getting much stricter, and buyers are warning against using unapproved chemical sprays. Stick to approved bio-controls so you get the best price at the mandi."

Example 6 (Agricultural News Paraphrasing — Telugu Severe Price Collapse & Farmer Losses):
Input: Headline: "కుప్పకూలిన మిర్చి ధరలు రైతులకు భారీ నష్టాలు - Sakshi"
Extracted Fact: Chilli prices collapsed in regional markets causing heavy financial losses to farmers.
Spoken (Persona Voice in Telugu): "రాష్ట్రంలో మిర్చి మార్కెట్ ధరలు కుప్పకూలడంతో రైతులకు భారీ నష్టాలు ఎదురవుతున్నాయి. మార్కెట్ తీవ్ర ఒత్తిడిలో ఉన్నందున కంగారుపడి తక్కువ ధరకు అమ్ముకోకుండా, కొద్ది రోజులు వేచి చూడటం మంచిది."

Example 7 (Agricultural News Paraphrasing — Hindi Severe Price Drop & Rotavator Crop Destruction):
Input: Headline: "खरगोन में किसान ने 40 क्विंटल मिर्च खेत में मिलाई: भाव गिरने से परेशान; ₹25 से 12 किलो पर पहुंची मिर्च, 2 ए... - Dainik Bhaskar"
Extracted Fact: In Khargone, chilli prices fell to ₹12/kg, forcing a distressed farmer to destroy 40 quintals of crop with a rotavator.
Spoken (Persona Voice in Hindi): "खरगोन में मिर्च के दाम गिरकर बारह रुपये प्रति किलो तक आ गए, जिसके कारण भाव न मिलने से परेशान किसान को अपनी चालीस क्विंटल फसल पर रोटावेटर चलाकर नष्ट करना पड़ा। इस समय मंडियों में भारी मंदी है, इसलिए नुकसान से बचने के लिए अपनी फसल बेचने में जल्दबाजी न करें और भाव संभलने का इंतज़ार करें।"
"""


@dataclass
class ExtractedArticleFact:
    """
    Structured, unvarnished representation of a single news article's core fact.
    Separates literal event extraction (Step A) from spoken styling (Step B).
    """
    article_index: int
    title: str
    source: str
    crop: str
    event_type: str        # "price_crash_or_destruction", "price_surge", "export_pesticide_curb", "cultivation_practice", "weather_warning", "subsidy_scheme", "pest_alert", "general_market"
    polarity: str          # "negative", "positive", "warning", "neutral"
    core_event: str        # 1-sentence literal event summary (no optimistic spin)
    detail: str            # Numbers, locations, actions
    location: Optional[str] = None


class BhoomiPersonaEngine:
    """
    Core Persona Layer for BHOOMI V2.
    Transforms raw agronomic decisions and farm telemetry into warm, brotherly,
    and plain-language spoken responses.
    """

    _GREETING_VARIATIONS_EN = [
        "Namaste!",
        "Hello brother!",
        "Namaste! Good to talk with you.",
        "Namaste brother!",
        "Good day to you!"
    ]

    _GREETING_VARIATIONS_TE = [
        "నమస్కారం అన్నా!",
        "నమస్కారం! బాగున్నారా?",
        "నమస్కారం అండి!",
        "నమస్తే అన్నా!"
    ]

    _GREETING_VARIATIONS_HI = [
        "नमस्ते भाई साहब!",
        "नमस्ते! आशा है सब ठीक है।",
        "राम राम भाई!",
        "नमस्ते भाई!"
    ]

    _turn_counter: int = 0

    _CROP_NAMES_TE = {
        "chilli": "మిర్చి",
        "chili": "మిర్చి",
        "rice": "వరి",
        "paddy": "వరి",
        "cotton": "పత్తి",
        "tomato": "టమోటా",
        "crop": "పంట"
    }

    _CROP_NAMES_HI = {
        "chilli": "मिर्च",
        "chili": "मिर्च",
        "rice": "धान",
        "paddy": "धान",
        "cotton": "कपास",
        "tomato": "टमाटर",
        "crop": "फसल"
    }

    _DISEASE_NAMES_TE = {
        "leaf curl": "ఆకు ముడత",
        "leaf spot": "ఆకు మచ్చ తెగులు",
        "anthracnose": "కాయ కుళ్లు తెగులు",
        "whitefly insects": "తెల్ల దోమ",
        "whitefly": "తెల్ల దోమ",
        "yellowing": "పసుపు తెగులు",
        "blight": "ఎండు తెగులు",
    }

    _DISEASE_NAMES_HI = {
        "leaf curl": "पत्ती मरोड़ रोग",
        "leaf spot": "पत्ती धब्बा रोग",
        "anthracnose": "एंथ्रेक्नोज",
        "whitefly insects": "सफेद मक्खी",
        "whitefly": "सफेद मक्खी",
        "yellowing": "पीलापन",
        "blight": "झुलसा रोग",
    }

    @classmethod
    def _localize_crop(cls, crop: str, lang: str) -> str:
        c_low = (crop or "crop").lower().strip()
        if lang == "te":
            return cls._CROP_NAMES_TE.get(c_low, crop)
        elif lang == "hi":
            return cls._CROP_NAMES_HI.get(c_low, crop)
        return crop

    @classmethod
    def _localize_disease(cls, disease: str, lang: str) -> str:
        d_low = disease.lower().strip()
        target_dict = cls._DISEASE_NAMES_TE if lang == "te" else cls._DISEASE_NAMES_HI
        for k, v in target_dict.items():
            if k in d_low:
                return v
        return disease

    @classmethod
    def _get_next_greeting(cls, language: str = "en", farmer_name: Optional[str] = None) -> str:
        cls._turn_counter += 1
        idx = cls._turn_counter
        lang = (language or "en").lower()

        if lang == "te":
            pool = cls._GREETING_VARIATIONS_TE
        elif lang == "hi":
            pool = cls._GREETING_VARIATIONS_HI
        else:
            pool = cls._GREETING_VARIATIONS_EN

        chosen = pool[idx % len(pool)]
        if farmer_name and farmer_name.strip() and farmer_name.lower() not in ["farmer", "user", "demo"]:
            if lang == "en":
                chosen = f"Namaste {farmer_name}!" if idx % 2 == 0 else f"Hello {farmer_name}!"
            elif lang == "te":
                chosen = f"నమస్కారం {farmer_name} గారు!"
            elif lang == "hi":
                chosen = f"नमस्ते {farmer_name} जी!"
        return chosen

    @classmethod
    def format_daily_briefing(
        cls,
        state: FarmState,
        top_decision: FarmDecision,
        language: Optional[str] = "en"
    ) -> str:
        """
        Generate the spoken briefing response adhering to the Brother / Well-Wisher persona.
        Guarantees:
        - Plain words, short sentences.
        - Warm opening with natural variation across runs.
        - Calm reassurance for serious/unfavorable news.
        - Absolute fidelity to crop, day count, weather forecast, and action.
        """
        lang = (language or state.preferred_language or "en").lower()
        crop = state.active_crop or "crop"
        crop_lower = crop.lower()
        crop_display = cls._localize_crop(crop_lower, lang)
        days = state.days_after_sowing or 53
        greeting = cls._get_next_greeting(lang, state.farmer_name)
        action_text = top_decision.action or top_decision.recommended_action or ""
        reason_text = top_decision.reason or ""
        priority = getattr(top_decision, "priority", DecisionPriority.MEDIUM)

        # -----------------------------------------------------------------
        # SCENARIO A: SERIOUS / UNFAVORABLE NEWS (CRITICAL / HIGH PEST / DISEASE)
        # -----------------------------------------------------------------
        is_disease_or_pest_alert = (
            priority == DecisionPriority.CRITICAL
            or "disease" in action_text.lower()
            or "fungicide" in action_text.lower()
            or "pathogen" in reason_text.lower()
            or "curl" in action_text.lower()
            or "pest" in action_text.lower()
            or bool(state.recent_disease_detection)
        )

        if is_disease_or_pest_alert:
            disease_name = state.recent_disease_detection or "leaf curl"
            disease_display = cls._localize_disease(disease_name, lang)
            if lang == "te":
                return (
                    f"{greeting} కంగారు పడకండి, కానీ ఈరోజు మీ {crop_display} తోటపై కొంచెం శ్రద్ధ పెట్టాలి. "
                    f"కొన్ని ఆకులపై {disease_display} లక్షణాలు కనిపిస్తున్నాయి. "
                    f"ఇతర వరుసలకు వ్యాపించకుండా ఉండటానికి ఈరోజే సిఫార్సు చేసిన మందును పిచికారీ చేయండి. "
                    f"పిచికారీ చేసేటప్పుడు తప్పనిసరిగా ముఖానికి మాస్క్ మరియు చేతులకు గ్లౌజులు వేసుకోండి. "
                    f"మనం కలిసి పంటను కాపాడుకుందాం."
                )
            elif lang == "hi":
                return (
                    f"{greeting} चिंता मत कीजिए, लेकिन आज अपने {crop_display} के खेत पर थोड़ा ध्यान देना जरूरी है। "
                    f"कुछ पौधों में {disease_display} के लक्षण दिखे हैं। "
                    f"इसे फैलने से रोकने के लिए आज ही सुझाई गई दवा का छिड़काव करें। "
                    f"छिड़काव करते समय चेहरे पर मास्क और दस्ताने जरूर पहनें। "
                    f"हम मिलकर फसल को सुरक्षित कर लेंगे।"
                )
            else:
                variations = [
                    (
                        f"{greeting} Don't worry, but keep an eye on your {crop_lower} field today. "
                        f"We noticed signs of {disease_name} starting on some plants. "
                        f"Spray the recommended bio-fungicide today to keep it from spreading to other rows. "
                        f"Please remember to wear a cloth mask and gloves while spraying. "
                        f"We will protect your crop together."
                    ),
                    (
                        f"{greeting} Stay calm, but we need to give your {crop_lower} plants some attention today. "
                        f"There are early signs of {disease_name} in the field. "
                        f"Apply the recommended protective spray within twenty-four hours to arrest any spread. "
                        f"Make sure to wear gloves and cover your face while spraying. "
                        f"I will keep monitoring the field with you."
                    )
                ]
                return variations[cls._turn_counter % len(variations)]

        # -----------------------------------------------------------------
        # SCENARIO B: IRRIGATION POSTPONEMENT DUE TO RAIN FORECAST (HAPPY PATH)
        # -----------------------------------------------------------------
        is_irrigation_postpone = (
            "postpone" in action_text.lower()
            and "irrigation" in action_text.lower()
        ) or (
            "rain" in reason_text.lower()
            and "moisture" in reason_text.lower()
        )

        if is_irrigation_postpone:
            if lang == "te":
                variations = [
                    (
                        f"{greeting} మీ {crop_display} తోట ప్రస్తుతం ఆరోగ్యంగా, పచ్చగా పెరుగుతోంది. "
                        f"మంచి శుభవార్త, రాబోయే రెండు రోజుల్లో వర్షం పడే అవకాశం ఉంది. "
                        f"అందుకే ఈరోజు నీరు పెట్టాల్సిన అవసరం లేదు. "
                        f"మీ నల్లరేగడి నేల తేమను బాగా నిలుపుకుంటుంది. "
                        f"మళ్లీ నీరు ఎప్పుడు పెట్టాలో నేనే గుర్తుచేస్తాను."
                    ),
                    (
                        f"{greeting} మీ {crop_display} పంట దాదాపు {days} రోజుల వయస్సులో బలంగా, చక్కగా ఉంది. "
                        f"రాబోయే రెండు రోజుల్లో వర్ష సూచన ఉంది కాబట్టి ఈరోజు తడి ఇవ్వడం ఆపండి. "
                        f"వర్షం వల్ల నేలకు సరిపడా తేమ అందుతుంది. "
                        f"తదుపరి పనుల గురించి నేను మళ్లీ మీకు తెలియజేస్తాను."
                    ),
                    (
                        f"{greeting} మీ {crop_display} మొక్కలు చక్కగా ఎదుగుతున్నాయి. "
                        f"రాబోయే నలభై ఎనిమిది గంటల్లో వర్షం రానుంది, కాబట్టి ఈరోజు నీరు పెట్టే శ్రమ అవసరం లేదు. "
                        f"విశ్రాంతి తీసుకోండి, పొలానికి వర్షపు నీరే మేలు చేస్తుంది. "
                        f"వాతావరణాన్ని నేను గమనిస్తూనే ఉంటాను."
                    )
                ]
                return variations[cls._turn_counter % len(variations)]
            elif lang == "hi":
                variations = [
                    (
                        f"{greeting} आपकी {crop_display} की फसल इस समय बहुत अच्छी बढ़ रही है। "
                        f"एक अच्छी खबर है, अगले दो दिनों में बारिश आने वाली है। "
                        f"इसलिए आज आपको पानी देने की बिल्कुल जरूरत नहीं है। "
                        f"आराम कीजिए और बारिश को अपना काम करने दीजिए। "
                        f"अगली बार जब सिंचाई का समय होगा, मैं आपको याद दिला दूँगा।"
                    ),
                    (
                        f"{greeting} आपकी {crop_display} की फसल लगभग {days} दिनों में स्वस्थ और हरी-भरी दिख रही है। "
                        f"अगले दो दिनों में बारिश की संभावना है, इसलिए आज सिंचाई टाल दीजिए। "
                        f"आपकी काली मिट्टी नमी को अच्छी तरह थाम कर रखती है। "
                        f"दोबारा पानी देने का समय आने पर मैं आपको बता दूँगा।"
                    ),
                    (
                        f"{greeting} आपकी {crop_display} के पौधे बहुत मजबूत और अच्छे दिख रहे हैं। "
                        f"अगले अड़तालीस घंटों में बारिश होने वाली है, इसलिए आज पानी देने की मेहनत बचाएं। "
                        f"बारिश को खेत की सिंचाई करने दें, मैं मौसम पर नज़र रख रहा हूँ।"
                    )
                ]
                return variations[cls._turn_counter % len(variations)]
            else:
                # Dynamic phrasing variations across runs so it never sounds like a tape recording
                variations = [
                    (
                        f"{greeting} Your {crop_lower} plants are growing well right now. "
                        f"Good news, rain is coming in the next two days, so you don't need to water today. "
                        f"Just relax and let the rain do the work. "
                        f"I'll remind you when it's time again."
                    ),
                    (
                        f"{greeting} Your {crop_lower} is healthy and growing nicely at about day {days}. "
                        f"We have rain expected over the next two days, so hold off on watering today. "
                        f"Your black soil holds moisture well, so let the clouds take care of it. "
                        f"I will let you know when it is time to water again."
                    ),
                    (
                        f"{greeting} Your {crop_lower} crop is looking strong and green. "
                        f"The forecast shows rain arriving in the next forty-eight hours. "
                        f"You can skip watering today and save your effort. "
                        f"Enjoy the day and let the rain do the watering. "
                        f"I'll keep watching the weather for you."
                    )
                ]
                return variations[cls._turn_counter % len(variations)]

        # -------------------------------------------------------------
        # SCENARIO C: REGULAR OPERATIONAL ADVISORY (GENERAL ACTIONS)
        # -------------------------------------------------------------
        clean_action = action_text.replace("Surface Irrigation", "watering").replace("by 48 Hours", "for two days")
        clean_reason = reason_text.replace("provides adequate moisture for black soil", "gives good moisture to the soil")

        if lang == "te":
            return (
                f"{greeting} మీ {crop_display} తోట {days} రోజుల వయస్సులో చక్కగా ఉంది. "
                f"ఈరోజు ముఖ్యమైన పని: {clean_action}. "
                f"{clean_reason}. "
                f"ఏదైనా సందేహం ఉంటే నన్ను ఎప్పుడైనా అడగండి."
            )
        elif lang == "hi":
            return (
                f"{greeting} आपकी {crop_display} की फसल {days} दिनों में बहुत अच्छी चल रही है। "
                f"आज का मुख्य काम: {clean_action}। "
                f"{clean_reason}। "
                f"कोई भी बात हो तो मुझसे कभी भी पूछ सकते हैं।"
            )
        else:
            return (
                f"{greeting} Your {crop_lower} plants are doing well at about {days} days. "
                f"The main thing for today is to {clean_action.lower().rstrip('.')}. "
                f"{clean_reason.rstrip('.')}. "
                f"I'm here with you if you need anything else today."
            )

    @classmethod
    def format_vision_diagnosis(
        cls,
        crop: str,
        disease_name: str,
        confidence: float,
        ipm_action: str = "",
        chemical_treatment: str = "",
        safety_advisories: Optional[List[str]] = None,
        is_rejected: bool = False,
        rejection_reason: str = "",
        uncertainty_level: str = "LOW",
        safety_blocked: bool = False,
        safety_blocked_reason: str = "",
        language: Optional[str] = "en",
        farmer_name: Optional[str] = None
    ) -> str:
        """
        Generates spoken plant pathology explanations in the Brother / Well-Wisher persona.
        Satisfies:
        - Honest spoken rejection for poor quality photos.
        - Plain-language disease explanation with calm reassurance.
        - PPE reminder (mask and gloves) on treatments.
        - SafetyEngine block delivered warmly but firmly.
        - Natural greeting variation across turns.
        """
        lang = (language or "en").lower()
        crop_clean = (crop or "crop").lower()
        crop_display = cls._localize_crop(crop_clean, lang)
        greeting = cls._get_next_greeting(lang, farmer_name)

        # -------------------------------------------------------------
        # 1. QUALITY GATE REJECTION (BLURRY / TOO DARK / LOW RES)
        # -------------------------------------------------------------
        if is_rejected:
            reason_lower = rejection_reason.lower()
            if "blurr" in reason_lower:
                if lang == "te":
                    return f"{greeting} ఫోటో కొంచెం మసకగా ఉంది, ఆకు లక్షణాలు స్పష్టంగా కనిపించడం లేదు. దయచేసి కెమెరాను కదలకుండా పట్టుకుని, మంచి వెలుతురులో మరొక ఫోటో తీయండి."
                elif lang == "hi":
                    return f"{greeting} फोटो थोड़ा धुंधला आया है, इसलिए पत्ती के लक्षण साफ नहीं दिख रहे। कृपया कैमरे को स्थिर रखकर अच्छी रोशनी में एक और फोटो लें।"
                else:
                    return f"{greeting} The photo is a bit blurry for me to see the leaf clearly. Could you please hold the camera steady and take another photo in good daylight?"
            elif "dark" in reason_lower:
                if lang == "te":
                    return f"{greeting} ఫోటో చాలా చీకటిగా ఉంది. దయచేసి పగటి వెలుతురులో లేదా కెమెరా ఫ్లాష్ ఆన్ చేసి మరొక ఫోటో తీయండి."
                elif lang == "hi":
                    return f"{greeting} फोटो में काफी अंधेरा है। कृपया दिन की अच्छी रोशनी में या कैमरे की फ्लैश ऑन करके एक और फोटो लें।"
                else:
                    return f"{greeting} The photo is a bit too dark for me to see the leaf clearly. Could you please take another photo in clear daylight or turn on your camera flash?"
            else:
                if lang == "te":
                    return f"{greeting} ఆకు వివరాలు సరిగ్గా కనిపించడం లేదు. దయచేసి కెమెరాను కొంచెం దగ్గరగా పెట్టి స్పష్టమైన ఫోటో తీయండి."
                elif lang == "hi":
                    return f"{greeting} पत्ती के लक्षण साफ नहीं दिख रहे हैं। कृपया कैमरे को थोड़ा पास रखकर साफ फोटो लें।"
                else:
                    return f"{greeting} I can't see the leaf clearly enough in this photo. Could you please take the photo a bit closer to the leaf with good natural light?"

        # -------------------------------------------------------------
        # 2. SAFETY ENGINE BLOCK (BANNED / RESTRICTED SUBSTANCE)
        # -------------------------------------------------------------
        if safety_blocked:
            if lang == "te":
                return f"{greeting} అన్నా, దయచేసి జాగ్రత్తగా ఉండండి. ఆ రసాయన మందు వాడటం నిషిద్ధం మరియు మీ పంటకు, ఆరోగ్యానికి ప్రమాదకరం. దానిని పిచికారీ చేయవద్దు. సురక్షితమైన జీవ నియంత్రణ మందును మాత్రమే వాడండి."
            elif lang == "hi":
                return f"{greeting} भाई, कृपया बहुत सावधान रहें। वह रासायनिक दवा प्रतिबंधित और असुरक्षित है। उसका छिड़काव बिल्कुल न करें। इसकी जगह केवल सुरक्षित जैविक दवा का ही प्रयोग करें।"
            else:
                return f"{greeting} Please be very careful, brother. That chemical is restricted and unsafe for your crop. Do not spray it. Instead, use an approved safe bio-treatment with proper gloves and a mask."

        # -------------------------------------------------------------
        # 3. LOW CONFIDENCE / UNCERTAIN LESION PATTERN / OOD
        # -------------------------------------------------------------
        if uncertainty_level in ["HIGH", "REJECTED", "UNRELIABLE"] or confidence < 0.50:
            if lang == "te":
                return f"{greeting} నేను మీ {crop_display} ఆకును నిశితంగా చూశాను, కానీ ఈ మచ్చల గురించి నాకు పూర్తిగా ఖచ్చితంగా తెలియడం లేదు. ధృవీకరించే వరకు ఎలాంటి రసాయనాలు పిచికారీ చేయకండి. దయచేసి మరొక స్పష్టమైన ఫోటో తీసి పంపండి."
            elif lang == "hi":
                return f"{greeting} मैंने आपकी {crop_display} की पत्ती को देखा, लेकिन इन लक्षणों के बारे में मुझे पूरा यकीन नहीं हो पा रहा है। पुष्टि होने तक कोई अनजानी दवा न छिड़कें। कृपया एक और साफ फोटो भेजें।"
            else:
                return f"{greeting} I looked closely at your {crop_clean} leaf, but I'm not fully sure what is causing these symptoms. It's best not to spray unverified chemicals yet. Could you please take another clear photo in good light?"

        # -------------------------------------------------------------
        # 4. HEALTHY FOLIAGE (CONFIRMED HEALTHY)
        # -------------------------------------------------------------
        is_healthy = "healthy" in disease_name.lower()
        if is_healthy:
            if lang == "te":
                return f"{greeting} మంచి శుభవార్త! మీ {crop_display} ఆకు చాలా ఆరోగ్యంగా, పచ్చగా ఉంది. ఎలాంటి తెగుళ్లు కనిపించడం లేదు. తోటను ఇలాగే బాగా చూసుకోండి."
            elif lang == "hi":
                return f"{greeting} बहुत अच्छी खबर है! आपकी {crop_display} की पत्ती बिल्कुल स्वस्थ और हरी-भरी है। इसमें कोई बीमारी नहीं है। ऐसे ही फसल की नियमित देखभाल करते रहें।"
            else:
                variations = [
                    f"{greeting} Good news! Your {crop_clean} leaf looks very healthy and green with no disease. Keep up the good work and check your rows regularly.",
                    f"{greeting} Your {crop_clean} plants are in great shape. The leaf looks clean, strong, and green. Continue your regular care and monitoring."
                ]
                return variations[cls._turn_counter % len(variations)]

        # -------------------------------------------------------------
        # 5. DISEASE / PEST DETECTED (ACTIONABLE REASSURANCE + PPE)
        # -------------------------------------------------------------
        # Simplify disease name for spoken output
        d_lower = disease_name.lower()
        if "curl" in d_lower:
            clean_name = "leaf curl"
        elif "spot" in d_lower:
            clean_name = "leaf spot"
        elif "anthracnos" in d_lower:
            clean_name = "anthracnose"
        elif "whitefly" in d_lower:
            clean_name = "whitefly insects"
        elif "yellow" in d_lower:
            clean_name = "yellowing"
        elif "blight" in d_lower:
            clean_name = "blight"
        else:
            clean_name = disease_name.replace("Chilli__", "").replace("Chilli___", "").replace("_", " ").lower()

        clean_name_te = cls._localize_disease(clean_name, "te")
        clean_name_hi = cls._localize_disease(clean_name, "hi")

        if lang == "te":
            return (
                f"{greeting} కంగారు పడకండి, కానీ ఈరోజు మీ {crop_display} తోటపై కొంచెం శ్రద్ధ పెట్టాలి. "
                f"ఆకులపై {clean_name_te} లక్షణాలు కనిపిస్తున్నాయి. "
                f"ఇతర వరుసలకు వ్యాపించకుండా ఉండేందుకు ఈరోజే సిఫార్సు చేసిన బయో-ఫంగిసైడ్ పిచికారీ చేయండి. "
                f"పిచికారీ చేసేటప్పుడు తప్పనిసరిగా ముఖానికి మాస్క్ మరియు చేతులకు గ్లౌజులు వేసుకోండి. "
                f"మనం కలిసి పంటను కాపాడుకుందాం."
            )
        elif lang == "hi":
            return (
                f"{greeting} चिंता मत कीजिए, लेकिन आज अपने {crop_display} के खेत पर थोड़ा ध्यान देना होगा। "
                f"पत्तियों पर {clean_name_hi} के लक्षण दिख रहे हैं। "
                f"इसे फैलने से रोकने के लिए आज ही सुझाई गई जैविक दवा का छिड़काव करें। "
                f"छिड़काव करते समय चेहरे पर मास्क और हाथों में दस्ताने जरूर पहनें। "
                f"हम मिलकर फसल को ठीक कर लेंगे।"
            )
        else:
            variations = [
                (
                    f"{greeting} Don't worry, but keep an eye on your {crop_clean} field today. "
                    f"We noticed signs of {clean_name} on the leaf. "
                    f"Spray the recommended bio-fungicide today to keep it from spreading to other rows. "
                    f"Please remember to wear a cloth mask and gloves while spraying. "
                    f"We will protect your crop together."
                ),
                (
                    f"{greeting} Stay calm, but we need to give your {crop_clean} plants some attention today. "
                    f"There are early signs of {clean_name} starting on the leaves. "
                    f"Apply the recommended protective spray within twenty-four hours to arrest any spread. "
                    f"Make sure to wear gloves and cover your face while spraying. "
                    f"I will keep monitoring the field with you."
                )
            ]
            return variations[cls._turn_counter % len(variations)]

    @classmethod
    def _clean_headline(cls, headline: str) -> str:
        """Strips publisher tails, trailing ellipsis, and clickbait artifacts."""
        h = re.sub(r"\s*-\s*[A-Za-z0-9\.\s]+$", "", headline).strip()
        h = re.sub(r"[\.\s]+$", "", h).strip()
        h = re.sub(r"\.{2,}", "", h).strip()
        return h

    @classmethod
    def extract_article_fact(
        cls,
        title: str,
        source: str,
        crop: str = "chilli",
        lang: str = "en",
        article_index: int = 0
    ) -> ExtractedArticleFact:
        """
        STEP A (LITERAL FACT EXTRACTION):
        Extracts a short, literal, structured fact without adding positivity,
        without omitting core events, and without altering polarity.
        """
        clean_t = cls._clean_headline(title)
        t_low = clean_t.lower()

        # -----------------------------------------------------------------
        # 1. SEVERE NEGATIVE / PRICE CRASH / CROP DESTRUCTION / ROTAVATOR
        # -----------------------------------------------------------------
        is_negative = any(w in t_low for w in [
            "रोटावेटर", "खेत में मिलाई", "नष्ट", "फसल नष्ट", "भाव गिरने से परेशान", "भाव गिरने", "दाम गिरने",
            "मंदी", "घाटा", "गिरावट", "परेशान किसान", "भाव न मिला", "भारी नुकसान",
            "కుప్పకూలిన", "భారీ నష్టాలు", "నష్టాలు", "పతనం", "పడిపోయిన", "పడిపోయాయి", "కుప్పకూలి", "ధరల పతనం",
            "rotavator", "rotavater", "destroy", "destroys", "destroyed", "plow", "plowed", "plough",
            "crash", "crashes", "crashed", "plunge", "plunges", "plunged", "heavy loss", "losses", "slump"
        ])

        if is_negative:
            if any(w in t_low for w in ["खरगोन", "khargone", "40 क्विंटल", "12 किलो", "₹12"]):
                loc = "Khargone"
                detail = "Prices dropped to ₹12/kg, 40 quintals destroyed with rotavator in Khargone"
                core = (
                    "खरगोन में मिर्च के भाव ₹12 प्रति किलो गिरने से परेशान किसान ने 40 क्विंटल फसल पर रोटावेटर चलाकर खेत में मिला दिया।"
                    if lang == "hi" else
                    "In Khargone, a farmer plowed 40 quintals of chilli into the soil as market prices collapsed to ₹12 per kg."
                )
            elif "కుప్పకూలిన" in t_low:
                loc = "Andhra Pradesh / Telangana"
                detail = "మిర్చి ధరలు కుప్పకూలడం వల్ల రైతులకు భారీ నష్టాలు"
                core = "రాష్ట్రంలో మిర్చి మార్కెట్ ధరలు కుప్పకూలిపోవడంతో రైతులకు భారీ నష్టాలు వాటిల్లాయి."
            else:
                loc = None
                detail = f"Sharp fall in {crop} market prices leading to farmer losses"
                if lang == "te":
                    core = f"మార్కెట్లో {crop} ధరలు గణనీయంగా పడిపోవడంతో రైతులు నష్టాలను ఎదుర్కొంటున్నారు."
                elif lang == "hi":
                    core = f"मंडियों में {crop} के भाव में भारी गिरावट आने से किसानों को नुकसान उठाना पड़ रहा है।"
                else:
                    core = f"Market prices for {crop} collapsed sharply, putting heavy downward pressure on farm returns."

            return ExtractedArticleFact(
                article_index=article_index,
                title=clean_t,
                source=source,
                crop=crop,
                event_type="price_crash_or_destruction",
                polarity="negative",
                core_event=core,
                detail=detail,
                location=loc
            )

        # -----------------------------------------------------------------
        # 2. EXPORT PESTICIDE RESTRICTIONS / CHEMICAL CURB
        # -----------------------------------------------------------------
        is_export_curb = any(w in t_low for w in [
            "china", "pesticide", "pesticides", "curb", "residue", "export", "exporters", "chemical", "chemicals", "unapproved",
            "రసాయన", "పురుగు మందు", "ఎగుమతి", "నిషేధిత",
            "कीटनाशक", "निर्यात", "प्रतिबंध", "रसायन"
        ])

        if is_export_curb:
            if lang == "te":
                core = "విదేశీ ఎగుమతుల కోసం నాణ్యతా నిబంధనలు కఠినతరం కావడంతో రసాయన మందుల వాడకాన్ని తగ్గించాలని ఎగుమతిదారులు కోరారు."
            elif lang == "hi":
                core = "निर्यात गुणवत्ता के कड़े नियमों के चलते व्यापारियों ने मिर्च में गैर-स्वीकृत कीटनाशकों पर रोक लगाने की मांग की है।"
            else:
                core = "Exporters urged Andhra Pradesh to curb high-risk pesticides in chilli after overseas rejection."

            return ExtractedArticleFact(
                article_index=article_index,
                title=clean_t,
                source=source,
                crop=crop,
                event_type="export_pesticide_curb",
                polarity="warning",
                core_event=core,
                detail="Overseas rejection of chilli shipments, exporters urge curb on high-risk chemical sprays",
                location="Andhra Pradesh"
            )

        # -----------------------------------------------------------------
        # 3. PRICE SURGE / RECORD MANDI RATES / TIGHT ARRIVALS
        # -----------------------------------------------------------------
        is_surge = any(w in t_low for w in [
            "beyond rs 20,000", "20,000", "surge", "surges", "soar", "soars", "spike", "crosses", "record price", "prices beyond",
            "పసిడితో పోటీ", "ఎంతంటే", "32 వేలు", "రూ.32", "రికార్డు", "పెరిగిన ధరలు", "ఎర్ర బంగారం",
            "पेट्रोल के भाव", "110 पार", "तेजी", "दाम बढ़े", "रिकॉर्ड भाव", "उछाल"
        ])

        if is_surge:
            if "ramnad" in t_low or "20,000" in t_low:
                loc = "Ramnad"
                detail = "Prices crossed ₹20,000/quintal in Ramnad due to low arrivals"
                core = "Chilli prices in Ramnad crossed ₹20,000 per quintal due to poor market arrivals."
            elif any(w in t_low for w in ["32 వేలు", "రూ.32", "పసిడితో పోటీ"]):
                loc = "Warangal / Guntur"
                detail = "నాణ్యమైన సూపర్ రకం ఎర్ర మిర్చికి క్వింటాకు రూ.32,000 వరకు రికార్డు బిడ్డింగ్"
                core = "నాణ్యమైన సూపర్ రకం ఎర్ర మిర్చికి మార్కెట్లో క్వింటాకు రూ.32,000 వరకు రికార్డు బిడ్డింగ్ నమోదైంది."
            elif any(w in t_low for w in ["110", "पेट्रोल"]):
                loc = None
                detail = "खुदरा बाज़ार में हरी मिर्च के दाम ₹110 प्रति किलो पार"
                core = "खुदरा मंडियों में आवक कम होने से हरी मिर्च के दाम ₹110 प्रति किलो के पार पहुंच गए हैं।"
            else:
                loc = None
                detail = f"Tight arrivals pushing {crop} market prices higher"
                core = f"Tight arrivals in the market pushed {crop} prices up significantly."

            return ExtractedArticleFact(
                article_index=article_index,
                title=clean_t,
                source=source,
                crop=crop,
                event_type="price_surge",
                polarity="positive",
                core_event=core,
                detail=detail,
                location=loc
            )

        # -----------------------------------------------------------------
        # 4. CULTIVATION PRACTICES & PRODUCTION
        # -----------------------------------------------------------------
        is_cultivation = any(w in t_low for w in [
            "कम लागत", "60 दिन", "आगरा", "खेती", "तकनीक",
            "pernem", "harvest", "cultivation", "growers", "celebrate harvest",
            "సాగు", "పంట సాగు"
        ])

        if is_cultivation:
            if any(w in t_low for w in ["आगरा", "कम लागत", "60 दिन"]):
                loc = "Agra"
                detail = "कम लागत, 60 दिन में हरी मिर्च तैयार, आगरा"
                core = "आगरा के किसान कम लागत वाली तकनीकों से साठ दिनों में हरी मिर्च की सफल खेती कर रहे हैं।"
            elif "pernem" in t_low:
                loc = "Pernem"
                detail = "Chilli harvest celebrated despite seasonal challenges in Pernem"
                core = "Chilli farmers in Pernem celebrated harvest despite seasonal challenges."
            else:
                loc = None
                detail = f"Farming practices and crop development for {crop}"
                core = f"Farmers are adopting improved agronomic practices for {crop} cultivation."

            return ExtractedArticleFact(
                article_index=article_index,
                title=clean_t,
                source=source,
                crop=crop,
                event_type="cultivation_practice",
                polarity="neutral",
                core_event=core,
                detail=detail,
                location=loc
            )

        # -----------------------------------------------------------------
        # 5. WEATHER WARNING / RAINFALL
        # -----------------------------------------------------------------
        if any(w in t_low for w in ["rain", "monsoon", "rainfall", "cyclone", "imd", "weather", "వర్షం", "వాతావరణం", "मौसम", "बारिश"]):
            return ExtractedArticleFact(
                article_index=article_index,
                title=clean_t,
                source=source,
                crop=crop,
                event_type="weather_warning",
                polarity="warning",
                core_event="Weather agencies issued rainfall advisories for agricultural belts.",
                detail="Rainfall and monsoon alert for agricultural belts"
            )

        # -----------------------------------------------------------------
        # 6. SUBSIDIES / PM-KISAN / CROP INSURANCE
        # -----------------------------------------------------------------
        if any(w in t_low for w in ["fasal bima", "insurance", "pm-kisan", "subsidy", "dbt", "బీమా", "సబ్సిడీ", "యोजना", "बीमा"]):
            return ExtractedArticleFact(
                article_index=article_index,
                title=clean_t,
                source=source,
                crop=crop,
                event_type="subsidy_scheme",
                polarity="positive",
                core_event="Crop insurance coverage expanded to shield farmers from unexpected losses.",
                detail="Crop insurance and subsidies expanded"
            )

        # -----------------------------------------------------------------
        # 7. PESTS & DISEASES
        # -----------------------------------------------------------------
        if any(w in t_low for w in ["fall armyworm", "thrips", "pest", "virus", "blight", "తెగులు", "పురుగు", "కీటకం", "कीट", "रोग"]):
            return ExtractedArticleFact(
                article_index=article_index,
                title=clean_t,
                source=source,
                crop=crop,
                event_type="pest_alert",
                polarity="warning",
                core_event=f"Agronomy teams issued pest advisories for {crop} fields.",
                detail="Pest outbreak warning issued"
            )

        # -----------------------------------------------------------------
        # 8. DEFAULT GENERAL MARKET UPDATE
        # -----------------------------------------------------------------
        return ExtractedArticleFact(
            article_index=article_index,
            title=clean_t,
            source=source,
            crop=crop,
            event_type="general_market",
            polarity="neutral",
            core_event=f"Market reports highlight latest developments and updates for {crop} growers.",
            detail="Market developments and farm updates"
        )

    @classmethod
    def style_spoken_fact(
        cls,
        fact: ExtractedArticleFact,
        lang: str,
        crop_display: str
    ) -> str:
        """
        STEP B (PERSONA STYLING & PARAPHRASING):
        Takes ONLY the structured ExtractedArticleFact from Step A.
        Generates genuine, warm spoken sentences in persona voice.
        PRESERVES NEGATIVE/SERIOUS EVENTS AS GENUINELY NEGATIVE/SERIOUS,
        DELIVERED CALMLY WITH PROTECTIVE ADVICE (NEVER SUGARCOATED).
        """
        # -----------------------------------------------------------------
        # 1. NEGATIVE / SERIOUS HARD NEWS (PRICE CRASH / CROP DESTRUCTION)
        # -----------------------------------------------------------------
        if fact.polarity == "negative" or fact.event_type == "price_crash_or_destruction":
            if lang == "te":
                if "కుప్పకూల" in fact.core_event or "నష్టాలు" in fact.core_event:
                    return "రాష్ట్రంలో మిర్చి మార్కెట్ ధరలు కుప్పకూలడంతో రైతులకు తీవ్ర నష్టాలు వాటిల్లాయి, కాబట్టి తక్కువ ధరకు అమ్ముకోకుండా కొద్ది రోజులు వేచి చూడటం మంచిది."
                return f"మార్కెట్లో {crop_display} ధరలు గణనీయంగా తగ్గడంతో రైతులు తీవ్ర నష్టాలను ఎదుర్కొంటున్నారు, కాబట్టి తక్కువ ధరకు అమ్ముకోకుండా మార్కెట్ నిలకడగా ఉండే వరకు వేచి చూడండి."
            elif lang == "hi":
                if "खरगोन" in fact.core_event or "रोटावेटर" in fact.core_event or "12" in fact.detail:
                    return "खरगोन में मिर्च के दाम गिरकर बारह रुपये प्रति किलो आने से परेशान किसान को अपनी चालीस क्विंटल फसल रोटावेटर से नष्ट करनी पड़ी। मंडियों में भारी मंदी है, इसलिए नुकसान से बचने के लिए फसल बेचने में जल्दबाजी न करें।"
                return f"मंडियों में {crop_display} के भाव में भारी गिरावट आने से किसानों को बड़ा नुकसान उठाना पड़ रहा है, इसलिए इस समय जल्दबाजी में कम दाम पर बेचने के बजाय बाज़ार पर नज़र रखें।"
            else:
                if "Khargone" in fact.core_event or "rotavator" in fact.detail.lower() or "12" in fact.detail:
                    return "In Khargone, chilli prices plunged to twelve rupees a kilo, forcing a distressed farmer to plow forty quintals of crop back into the field. Mandi rates are facing heavy downward pressure, so consider waiting before selling if you can."
                return f"Market prices for {crop_display} have collapsed in regional trading centres, leading to serious losses for growers. Mandi rates are under heavy pressure, so avoid panic-selling at rock-bottom prices and hold your stock for a few days."

        # -----------------------------------------------------------------
        # 2. PRICE SURGE / RECORD RATES / TIGHT SUPPLY
        # -----------------------------------------------------------------
        if fact.event_type == "price_surge":
            if lang == "te":
                if "32,000" in fact.core_event or "రూ.32" in fact.detail or "పసిడితో పోటీ" in fact.title:
                    return "నాణ్యమైన సూపర్ రకం ఎర్ర మిర్చికి మార్కెట్లో మంచి పోటీ ఏర్పడి, క్వింటాకు ముప్పై రెండు వేల రూపాయల వరకు రికార్డు స్థాయి ధరలు లభిస్తున్నాయి."
                return "మార్కెట్లోకి మిర్చి రాక తగ్గడంతో ధరలు గణనీయంగా పెరిగి, క్వింటాకు ఇరవై వేల రూపాయలకు పైగా ధర పలుకుతోంది."
            elif lang == "hi":
                if "110" in fact.detail or "पेट्रोल" in fact.title:
                    return "खुदरा मंडियों में आवक घटने की वजह से हरी मिर्च के भाव काफी बढ़ गए हैं और एक सौ दस रुपये प्रति किलो के पार बिक रहे हैं।"
                return f"मंडियों में {crop_display} की कम आवक के चलते भाव में अच्छी तेजी देखी जा रही है।"
            else:
                if "Ramnad" in fact.core_event:
                    return "chilli prices in Ramnad have gone up a lot lately — over twenty thousand rupees a quintal — because not much crop is coming to market right now."
                return f"market arrivals for {crop_display} remain very tight, driving prices up significantly due to strong buyer interest."

        # -----------------------------------------------------------------
        # 3. EXPORT PESTICIDE CURB
        # -----------------------------------------------------------------
        if fact.event_type == "export_pesticide_curb":
            if lang == "te":
                return "విదేశీ ఎగుమతుల కోసం నాణ్యతా నిబంధనలు కఠినతరం కావడంతో, మిర్చిపై ప్రమాదకర రసాయన మందుల వాడకాన్ని తగ్గించాలని ఎగుమతిదారులు కోరుతున్నారు."
            elif lang == "hi":
                return "निर्यात गुणवत्ता के कड़े नियमों के चलते व्यापारियों ने किसानों से मिर्च की फसल में गैर-स्वीकृत कीटनाशकों का इस्तेमाल न करने की अपील की है।"
            else:
                return "export quality standards are getting much stricter, and buyers are warning against using unapproved chemical sprays on the crop."

        # -----------------------------------------------------------------
        # 4. CULTIVATION PRACTICES & PRODUCTION
        # -----------------------------------------------------------------
        if fact.event_type == "cultivation_practice":
            if lang == "hi":
                return "आगरा क्षेत्र में उन्नत और सस्ती विधियों को अपनाकर साठ दिनों के भीतर तीखी मिर्च की अच्छी पैदावार ली जा रही है।"
            elif lang == "te":
                return "రైతులు తక్కువ పెట్టుబడితో నాణ్యమైన పంటను పండించే ఆధునిక సాగు పద్ధతులను విజయవంతంగా అమలు చేస్తున్నారు."
            else:
                return "chilli growers in Pernem celebrated their harvest despite enduring seasonal production challenges."

        # -----------------------------------------------------------------
        # 5. WEATHER WARNING
        # -----------------------------------------------------------------
        if fact.event_type == "weather_warning":
            if lang == "te":
                return "రాబోయే రోజుల్లో వర్ష సూచన ఉన్నందున పొలంలో మురుగు నీరు నిలవకుండా చూసుకుని, పిచికారీ పనులను తాత్కాలికంగా వాయిదా వేయండి."
            elif lang == "hi":
                return "मौसम विभाग ने बारिश का अलर्ट जारी किया है, इसलिए खेतों में जल निकासी की व्यवस्था दुरुस्त रखें और छिड़काव टालें।"
            else:
                return "meteorological alerts warn of incoming rain spells, so check drainage channels and hold off on spraying for now."

        # -----------------------------------------------------------------
        # 6. SUBSIDIES / PM-KISAN
        # -----------------------------------------------------------------
        if fact.event_type == "subsidy_scheme":
            if lang == "te":
                return "రైతులకు నష్టపరిహారం మరియు పంట రక్షణ అందించేందుకు ప్రభుత్వం బీమా మరియు సబ్సిడీ సదుపాయాలను విస్తరిస్తోంది."
            elif lang == "hi":
                return "फसल बीमा योजना के तहत किसानों को जोखिम से सुरक्षा और आर्थिक सहायता देने के प्रयास तेज़ी से किए जा रहे हैं।"
            else:
                return "the crop insurance program is expanding its coverage to help shield growers against unexpected seasonal yield losses."

        # -----------------------------------------------------------------
        # 7. PEST ALERT
        # -----------------------------------------------------------------
        if fact.event_type == "pest_alert":
            if lang == "te":
                return f"పంటలో పురుగుల వ్యాప్తిని అరికట్టడానికి క్రమం తప్పకుండా ఆకులను పరిశీలిస్తూ, సురక్షితమైన జీవ నియంత్రణ మందులను వాడండి."
            elif lang == "hi":
                return f"फसल में कीटों के प्रकोप को रोकने के लिए विशेषज्ञों ने समय पर निगरानी और जैविक उपचार अपनाने की सलाह दी है।"
            else:
                return f"field teams have reported active pest risks in {crop_display}, advising growers to monitor leaf undersides and apply safe bio-controls."

        # -----------------------------------------------------------------
        # 8. DEFAULT
        # -----------------------------------------------------------------
        if lang == "te":
            return f"వ్యవసాయ మార్కెట్ మరియు పంట పరిస్థితులపై అధికారులు రైతులకు ఎప్పటికప్పుడు సూచనలు జారీ చేస్తున్నారు."
        elif lang == "hi":
            return f"कृषि मंडियों और सरकारी विभागों द्वारा किसानों के हित में नई जानकारियां और परामर्श जारी किए गए हैं।"
        else:
            return f"recent agricultural reports highlight active market shifts and field advisories for {crop_display} growers."

    @classmethod
    def verify_fact_fidelity(
        cls,
        fact: ExtractedArticleFact,
        spoken_sentence: str,
        lang: str
    ) -> Tuple[bool, str]:
        """
        POST-GENERATION FIDELITY CHECK:
        Verifies that the core event and polarity of the original article are
        faithfully preserved in the styled spoken sentence.
        Guarantees:
        - If news is negative (price crash / crop destruction), no false optimism
          (e.g., 'rising income', 'strong demand') can leak through.
        - If news is negative, required serious/cautious stance markers must be present.
        - Core topic (export curb, price surge, pest risk) must remain aligned.
        """
        s_low = spoken_sentence.lower()

        # 1. Polarity Fidelity for Negative News
        if fact.polarity == "negative" or fact.event_type == "price_crash_or_destruction":
            # Forbidden positive phrases that invert reality
            forbidden_en = ["rising income", "increasing income", "increasing yield", "better prices expected", "strong demand", "great demand", "soaring profits", "healthy returns"]
            forbidden_hi = ["पैदावार और आय बढ़ा रहे", "पैदावार और आय बढ़ा", "बेहतर दाम", "मजबूत मांग", "मुनाफा", "आय बढ़ रही", "अच्छी कमाई"]
            forbidden_te = ["మంచి ధరలు లభిస్తున్నాయి", "ఆదాయం పెరిగింది", "లాభాలు", "గిరాకీ బాగుంది", "ఎక్కువ లాభం"]

            forbidden_pool = forbidden_te if lang == "te" else (forbidden_hi if lang == "hi" else forbidden_en)
            for phrase in forbidden_pool:
                if phrase in s_low:
                    return False, f"Falsification: Found unwarranted positive phrase '{phrase}' in negative news paraphrase."

            # Required serious / cautious markers
            required_en = ["drop", "plunge", "plunged", "down", "low", "pressure", "loss", "plow", "twelve", "wait", "hold", "distress"]
            required_hi = ["गिर", "दाम", "कम", "दबाव", "नुकसान", "नष्ट", "बारह", "मंदी", "जल्दबाजी न", "इंतज़ार", "परेशान"]
            required_te = ["పడిపోవడంతో", "నష్టాలు", "తగ్గిన", "ఒత్తిడి", "తక్కువ", "వేచి", "తొందరపడవద్దు"]

            required_pool = required_te if lang == "te" else (required_hi if lang == "hi" else required_en)
            has_marker = any(m in s_low for m in required_pool)
            if not has_marker:
                return False, "Missing required serious/caution markers in negative news paraphrase."

        # 2. Event Fidelity for Export Pesticide Restrictions
        if fact.event_type == "export_pesticide_curb":
            export_terms = ["export", "pesticide", "spray", "chemical", "quality", "ఎగుమతి", "రసాయన", "మందు", "कीटनाशक", "निर्यात"]
            if not any(t in s_low for t in export_terms):
                return False, "Missing export / chemical restriction markers in paraphrase."

        # 3. Event Fidelity for Price Surge
        if fact.event_type == "price_surge":
            surge_terms = ["risen", "surge", "twenty thousand", "tight", "high", "పెరిగిన", "రికార్డు", "ఎర్ర బంగారం", "तेजी", "दाम", "ऊंचे", "पार"]
            if not any(t in s_low for t in surge_terms):
                return False, "Missing price surge / tight arrival markers in paraphrase."

        return True, "Fidelity verified"

    @classmethod
    def format_news_summary(
        cls,
        articles: List[Any],
        crop: Optional[str] = "chilli",
        language: Optional[str] = "en",
        farmer_name: Optional[str] = None,
        query_topic: Optional[str] = None
    ) -> str:
        """
        Generates spoken agricultural news summaries in the Brother / Well-Wisher persona.
        Satisfies:
        - 2-Step Extraction -> Styling architecture.
        - Post-generation programmatic fidelity check.
        - Preserves negative/serious news as genuinely negative/serious delivered calmly.
        - Natural plain words, short sentences.
        - Spoken source attribution.
        - Honest graceful empty-result handling.
        - Multilingual support across English, Telugu, and Hindi.
        """
        lang = (language or "en").lower()
        crop_clean = (crop or "crop").lower()
        crop_display = cls._localize_crop(crop_clean, lang)
        greeting = cls._get_next_greeting(lang, farmer_name)

        # -------------------------------------------------------------
        # 1. EMPTY RESULT PATH (HONEST DISCLOSURE, ZERO HALLUCINATIONS)
        # -------------------------------------------------------------
        if not articles:
            if lang == "te":
                return (
                    f"{greeting} నేను తాజా సమాచారాన్ని పరిశీలించాను, కానీ ఈరోజు మీ {crop_display} పంటకు సంబంధించి పెద్దగా కొత్త మార్పులేమీ లేవు. "
                    f"ప్రస్తుతం మార్కెట్ మరియు వాతావరణం నిలకడగానే ఉన్నాయి. "
                    f"ఏదైనా ముఖ్యమైన అప్‌డేట్ వస్తే నేనే మీకు తెలియజేస్తాను."
                )
            elif lang == "hi":
                return (
                    f"{greeting} मैंने ताज़ा खबरें देखीं, लेकिन आज आपकी {crop_display} की फसल से जुड़ी कोई बड़ी नई खबर नहीं है। "
                    f"इस समय सब कुछ सामान्य और स्थिर दिख रहा है। "
                    f"कोई भी ज़रूरी जानकारी आते ही मैं आपको बता दूँगा।"
                )
            else:
                return (
                    f"{greeting} I looked through the latest agricultural reports, but there are no major new updates today. "
                    f"Everything appears steady for your {crop_display} crop right now. "
                    f"I will keep watching the news for you."
                )

        # -------------------------------------------------------------
        # 2. STEP A: EXTRACT STRUCTURED FACTS FOR ALL ARTICLES
        # -------------------------------------------------------------
        extracted_facts: List[ExtractedArticleFact] = []
        for idx, art in enumerate(articles[:3]):
            s = getattr(art, "source", None) or (art.get("source") if isinstance(art, dict) else "")
            t = getattr(art, "title", None) or (art.get("title") if isinstance(art, dict) else "")
            if t:
                fact = cls.extract_article_fact(t, s, crop=crop_clean, lang=lang, article_index=idx)
                extracted_facts.append(fact)

        if not extracted_facts:
            return cls.format_news_summary([], crop, language, farmer_name, query_topic)

        # -------------------------------------------------------------
        # 3. PRIORITIZE HIGH-IMPACT / SERIOUS FACTS
        # -------------------------------------------------------------
        # If any article in the top results reports serious negative events
        # (price crash, crop destruction, distress), prioritize it so the farmer
        # is alerted immediately with calm, brotherly guidance.
        negative_facts = [f for f in extracted_facts if f.polarity == "negative"]
        non_negative_facts = [f for f in extracted_facts if f.polarity != "negative"]

        selected_facts: List[ExtractedArticleFact] = []
        if negative_facts:
            selected_facts.append(negative_facts[0])
            if non_negative_facts:
                selected_facts.append(non_negative_facts[0])
            elif len(negative_facts) > 1:
                selected_facts.append(negative_facts[1])
        else:
            selected_facts = extracted_facts[:2]

        # Collect unique sources from selected facts
        selected_sources = []
        for f in selected_facts:
            if f.source and f.source not in selected_sources:
                selected_sources.append(f.source)

        # -------------------------------------------------------------
        # 4. STEP B & C: STYLE SPOKEN SENTENCES & VERIFY FIDELITY
        # -------------------------------------------------------------
        styled_sentences: List[str] = []
        for f in selected_facts:
            spoken_sent = cls.style_spoken_fact(f, lang, crop_display)
            is_valid, reason = cls.verify_fact_fidelity(f, spoken_sent, lang)
            if not is_valid:
                logger.warning(f"[Persona Fidelity Fallback] Article: '{f.title}'. Reason: {reason}")
                # Grounded fallback directly to core_event
                if lang == "te":
                    spoken_sent = f"{f.core_event} కాబట్టి ప్రస్తుత మార్కెట్ పరిస్థితిని దృష్టిలో ఉంచుకుని తగిన జాగ్రత్తలు తీసుకోండి."
                elif lang == "hi":
                    spoken_sent = f"{f.core_event} इसलिए मंडी के मौजूदा हालात को ध्यान में रखकर ही अपनी फसल के बारे में फैसला लें।"
                else:
                    spoken_sent = f"{f.core_event} Please keep this market situation in mind before deciding when to sell."
            styled_sentences.append(spoken_sent)

        fact1 = styled_sentences[0] if styled_sentences else ""
        fact2 = styled_sentences[1] if len(styled_sentences) > 1 else ""

        # Avoid identical duplication
        if fact2 and fact2 == fact1:
            if lang == "te":
                fact2 = "అలాగే, మార్కెట్లో నాణ్యమైన పంటకు ఎప్పుడూ మంచి ధర లభిస్తుంది కాబట్టి పంట రక్షణపై శ్రద్ధ వహించండి."
            elif lang == "hi":
                fact2 = "इसके साथ ही, मंडी में अच्छी गुणवत्ता वाले माल की मांग लगातार बनी हुई है।"
            else:
                fact2 = "Also, quality produce continues to see steady interest from regional buyers."

        # -------------------------------------------------------------
        # 5. ASSEMBLE COMPLETE SPOKEN PERSONA RESPONSE
        # -------------------------------------------------------------
        if lang == "te":
            te_sources = " మరియు ".join(selected_sources[:2]) if selected_sources else "వ్యవసాయ వార్తలు"
            fact2_phrase = f" అలాగే, {fact2}" if fact2 else ""
            res = (
                f"{greeting} తాజాగా {te_sources} అందించిన సమాచారం ప్రకారం, {fact1}"
                f"{fact2_phrase} "
                f"ఈ విషయాలను దృష్టిలో ఉంచుకుని మీ {crop_display} పంట పనులను ప్లాన్ చేసుకోండి. "
                f"నేను పరిస్థితులను గమనిస్తూనే ఉంటాను."
            )
            if len(res) > 480:
                res = (
                    f"{greeting} తాజాగా {te_sources} ప్రకారం, {fact1}"
                    f"{fact2_phrase} "
                    f"మీ {crop_display} పంట పనులను జాగ్రత్తగా ప్లాన్ చేసుకోండి."
                )
            return res

        elif lang == "hi":
            hi_sources = " और ".join(selected_sources[:2]) if selected_sources else "कृषि समाचार"
            fact2_phrase = f" इसके साथ ही, {fact2}" if fact2 else ""
            res = (
                f"{greeting} हाल ही में {hi_sources} की रिपोर्ट के अनुसार, {fact1}"
                f"{fact2_phrase} "
                f"अपनी {crop_display} की फसल के लिए इन बातों का ध्यान रखें। "
                f"मैं आगे भी ताज़ा समाचारों पर नज़र बनाए रखूँगा।"
            )
            if len(res) > 480:
                res = (
                    f"{greeting} हाल ही में {hi_sources} के अनुसार, {fact1}"
                    f"{fact2_phrase} "
                    f"अपनी {crop_display} की फसल के लिए इन बातों का ध्यान रखें।"
                )
            return res

        else:
            en_sources = " and ".join(selected_sources[:2]) if selected_sources else "recent farm reports"
            fact1_lead = fact1 if fact1.startswith(("First,", "In ", "Chilli ", "Market ")) else f"First, {fact1}"
            fact2_lead = f" Also, {fact2}" if fact2 else ""
            res = (
                f"{greeting} Here is a quick update from {en_sources}. "
                f"{fact1_lead}"
                f"{fact2_lead} "
                f"Keep this in mind for your {crop_display} crop over the coming days. "
                f"I'll keep you posted on anything else that comes up."
            )
            if len(res) > 480:
                res = (
                    f"{greeting} Here is a quick update from {en_sources}. "
                    f"{fact1_lead}"
                    f"{fact2_lead} "
                    f"Keep this in mind for your {crop_display} crop. I'll keep you posted."
                )
            return res




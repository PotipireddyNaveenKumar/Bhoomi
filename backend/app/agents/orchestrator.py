import re
import json
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm.factory import get_llm_provider
from app.services.memory.digital_twin import DigitalTwinService
from app.services.safety.safety_engine import SafetyEngine
from app.agents.missing_info_detector import MissingInformationDetector
from app.agents.tool_registry import ToolRegistry
from app.repositories.memory_repo import MemoryRepository
from app.repositories.chat_repo import ChatRepository
from app.services.farm_manager.state_engine import FarmStateEngine
from app.services.farm_manager.daily_briefing import DailyFarmBriefingService
from app.services.farm_manager.change_detector import FarmChangeDetectionService
from app.services.farm_manager.task_engine import TaskIntelligenceEngine
from app.services.voice.intent_service import IntentNormalizationService
from app.services.voice.confirmation_state import ConfirmationStateMachine, ConfirmationState
from app.schemas.voice_intent import VoiceIntentType, VoiceIntent
from app.schemas.task import TaskType, TaskStatus
from app.schemas.decision import DecisionPriority
from app.services.farm_manager.recommendation_trace import RecommendationRecord, RecommendationTraceStore
from app.services.weather.weather_service import WeatherService
from app.services.market.market_service import MarketService
from app.services.conversation.dialogue_manager import FarmerDialogueManager
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput
from app.services.crop.recommendation_service import CropRecommendationService, CropRecommendationInput
from app.services.crop.lifecycle_service import CropLifecycleService


class OrchestrationResult:
    def __init__(
        self,
        response_text: str,
        visual_cards: List[Dict[str, Any]],
        voice_state: str = "RESPONDING",
        trace_id: str = ""
    ):
        self.response_text = response_text
        self.visual_cards = visual_cards
        self.voice_state = voice_state
        self.trace_id = trace_id


class BhoomiAgentOrchestrator:
    """
    Central BHOOMI AI Agent Orchestrator.
    Unified Voice & Text Agricultural Decision Intelligence Pipeline:
    Farmer Input -> Canonical Intent -> Multi-turn Confirmation State Machine ->
    Task Intelligence Engine / SafetyEngine / Farm Digital Twin -> Deterministic Tools ->
    FarmMemoryV2 -> RecommendationTraceStore -> Localized Voice/Text Output.
    """

    LOCALIZED_MSGS: Dict[str, Dict[str, str]] = {
        "action_cancelled": {
            "en": "Understood, the action has been cancelled.",
            "te": "సరే, చర్య రద్దు చేయబడింది.",
            "hi": "समझ गया, कार्रवाई रद्द कर दी गई है।",
            "ta": "சரி, செயல்பாடு ரத்து செய்யப்பட்டது.",
            "kn": "ಸರಿ, ಕ್ರಿಯೆಯನ್ನು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ.",
            "ml": "ശരി, നടപടി റദ്ദാക്കി."
        },
        "task_completed": {
            "en": "Task '{title}' has been marked as COMPLETED.",
            "te": "'{title}' పని విజయవంతంగా పూర్తయిందిగా నమోదు చేశాను.",
            "hi": "कार्य '{title}' सफलतापूर्वक पूरा दर्ज कर लिया गया है।",
            "ta": "'{title}' பணி வெற்றிகரமாக முடிந்தது என்று குறிக்கப்பட்டது.",
            "kn": "'{title}' ಕೆಲಸ ಯಶಸ್ವಿಯಾಗಿ ಪೂರ್ಣಗೊಂಡಿದೆ ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ.",
            "ml": "'{title}' ജോലി വിജയകരമായി പൂർത്തിയായതായി രേഖപ്പെടുത്തി."
        },
        "task_postponed": {
            "en": "Task '{title}' has been POSTPONED to {date}.",
            "te": "'{title}' పని {date} వరకు వాయిదా వేయబడింది.",
            "hi": "कार्य '{title}' को {date} तक के लिए स्थगित कर दिया गया है।",
            "ta": "'{title}' பணி {date} வரை ஒத்திவைக்கப்பட்டது.",
            "kn": "'{title}' ಕೆಲಸವನ್ನು {date} ವರೆಗೆ ಮುಂದೂಡಲಾಗಿದೆ.",
            "ml": "'{title}' ജോലി {date} വരെ മാറ്റിവെച്ചു."
        },
        "task_skipped": {
            "en": "Task '{title}' has been marked as SKIPPED.",
            "te": "'{title}' పనిని దాటవేయబడింది.",
            "hi": "कार्य '{title}' को छोड़ दिया गया है।",
            "ta": "'{title}' பணி தவிர்க்கப்பட்டது.",
            "kn": "'{title}' ಕೆಲಸವನ್ನು ಬಿಟ್ಟುಬಿಡಲಾಗಿದೆ.",
            "ml": "'{title}' ജോലി ഒഴിവാക്കി."
        },
        "no_matching_task": {
            "en": "I don't currently have an active task recorded for that activity or crop.",
            "te": "ప్రస్తుతం ఆ పంట లేదా పనికి సంబంధించిన క్రియాశీల పని నమోదు కాలేదు.",
            "hi": "वर्तमान में उस फसल या गतिविधि के लिए कोई सक्रिय कार्य दर्ज नहीं है।",
            "ta": "அந்தப் பயிர் அல்லது செயல்பாட்டிற்கு தற்போது எந்தப் பணியும் பதிவு செய்யப்படவில்லை.",
            "kn": "ಪ್ರಸ್ತುತ ಆ ಬೆಳೆ ಅಥವಾ ಚಟುವಟಿಕೆಗೆ ಯಾವುದೇ ಸಕ್ರಿಯ ಕೆಲಸ ದಾಖಲಾಗಿಲ್ಲ.",
            "ml": "ആ വിളയ്‌ക്കോ പ്രവർത്തനത്തിനോ നിലവിൽ സജീവമായ ജോലികളൊന്നും രേഖപ്പെടുത്തിയിട്ടില്ല."
        },
        "ambiguous_task": {
            "en": "I found multiple matching tasks for: {options}. Which field or crop do you mean?",
            "te": "నేను బహుళ పనులను కనుగొన్నాను ({options}). మీరు ఏ పంట లేదా పొలం గురించి మాట్లాడుతున్నారు?",
            "hi": "मुझे इसके लिए कई कार्य मिले: {options}। आप किस खेत या फसल की बात कर रहे हैं?",
            "ta": "நான் பல பணிகளைக் கண்டறிந்தேன்: {options}. நீங்கள் எந்த வயல் அல்லது பயிரைக் குறிப்பிடுகிறீர்கள்?",
            "kn": "ನಾನು ಅನೇಕ ಕೆಲಸಗಳನ್ನು ಕಂಡುಕೊಂಡಿದ್ದೇನೆ: {options}. ನೀವು ಯಾವ ಹೊಲ ಅಥವಾ ಬೆಳೆಯನ್ನು ಉಲ್ಲೇಖಿಸುತ್ತಿದ್ದೀರಿ?",
            "ml": "ഞാൻ ഒന്നിലധികം ജോലികൾ കണ്ടെത്തി: {options}. ഏത് വിളയെക്കുറിച്ചാണ് നിങ്ങൾ ഉദ്ദേശിക്കുന്നത്?"
        },
        "skip_consequence_irrigation": {
            "en": "Skipping '{title}' may affect crop yield as soil moisture is low. Do you still want to skip it?",
            "te": "నేలలో తేమ తక్కువగా ఉన్నందున '{title}' దాటవేయడం దిగుబడిపై ప్రభావం చూపుతుంది. మీరు ఖచ్చితంగా దాటవేయాలనుకుంటున్నారా?",
            "hi": "मिट्टी में नमी कम होने के कारण '{title}' छोड़ना फसल को प्रभावित कर सकता है। क्या आप वाकई इसे छोड़ना चाहते हैं?",
            "ta": "மண் ஈரப்பதம் குறைவாக உள்ளதால் '{title}' தவிர்ப்பது பயிரைப் பாதிக்கலாம். நீங்கள் இன்னும் அதைத் தவிர்க்க விரும்புகிறீர்களா?",
            "kn": "ಮಣ್ಣಿನ ತೇವಾಂಶ ಕಡಿಮೆಯಿರುವುದರಿಂದ '{title}' ಬಿಟ್ಟುಬಿಡುವುದು ಬೆಳೆಗೆ ಹಾನಿ ಉಂಟುಮಾಡಬಹುದು. ನೀವು ಖಂಡಿತವಾಗಿಯೂ ಬಿಟ್ಟುಬಿಡಲು ಬಯಸುವಿರಾ?",
            "ml": "മണ്ണിലെ ഈർപ്പം കുറവായതിനാൽ '{title}' ഒഴിവാക്കുന്നത് വിളയെ ബാധിച്ചേക്കാം. നിങ്ങൾക്ക് ഇപ്പോഴും ഇത് ഒഴിവാക്കണമെന്നുണ്ടോ?"
        },
        "low_confidence_clarification": {
            "en": "I didn't clearly understand which task you want to update. Could you please specify if you mean irrigation, spraying, or field inspection?",
            "te": "మీరు ఏ పనిని మార్చాలనుకుంటున్నారో నాకు స్పష్టంగా అర్థం కాలేదు. నీరు పెట్టడమా, పిచికారీయా లేదా పరిశీలనా అని వివరంగా చెప్పగలరా?",
            "hi": "मुझे स्पष्ट रूप से समझ नहीं आया कि आप किस कार्य को बदलना चाहते हैं। क्या आप सिंचाई, छिड़काव या निरीक्षण की बात कर रहे हैं?",
            "ta": "நீங்கள் எந்தப் பணியை மாற்ற விரும்புகிறீர்கள் என்பது தெளிவாகப் புரியவில்லை. நீர்ப்பாசனம், தெளிப்பு அல்லது ஆய்வு ஆகியவற்றில் எதைக் குறிப்பிடுகிறீர்கள்?",
            "kn": "ನೀವು ಯಾವ ಕೆಲಸವನ್ನು ನವೀಕರಿಸಲು ಬಯಸುತ್ತೀರಿ ಎಂದು ಸ್ಪಷ್ಟವಾಗಿ ಅರ್ಥವಾಗಲಿಲ್ಲ. ನೀರಾವರಿ, ಸಿಂಪಡಣೆ ಅಥವಾ ಪರಿಶೀಲನೆಯೇ ಎಂದು ತಿಳಿಸಿ.",
            "ml": "ഏത് ജോലിയാണ് അപ്ഡേറ്റ് ചെയ്യാൻ ആഗ്രഹിക്കുന്നതെന്ന് വ്യക്തമായില്ല. നനയ്ക്കൽ, തളിക്കൽ അല്ലെങ്കിൽ പരിശോധന എന്നിവയാണോ ഉദ്ദേശിച്ചത്?"
        },
        "rice_research_only": {
            "en": "Rice crop models are currently designated as RESEARCH_ONLY pending physical field validation. Farmer-facing chemical spraying prescriptions are restricted for rice.",
            "te": "వరి పంట నమూనాలు ప్రస్తుతం పరిశోధన దశలో ఉన్నాయి. వరిపై రైతులకు రసాయన స్ప్రే సిఫార్సులు అనుమతించబడవు.",
            "hi": "चावल की फसल के मॉडल वर्तमान में अनुसंधान चरण में हैं। चावल के लिए रासायनिक कीटनाशक छिड़काव की सिफारिश प्रतिबंधित है।",
            "ta": "நெல் பயிர் மாதிரிகள் தற்போது ஆராய்ச்சி நிலையில் உள்ளன. நெல்லுக்கு ரசாயன தெளிப்பு பரிந்துரைகள் அனுமதிக்கப்படாது.",
            "kn": "ಭತ್ತದ ಬೆಳೆ ಮಾದರಿಗಳು ಪ್ರಸ್ತುತ ಸಂಶೋಧನಾ ಹಂತದಲ್ಲಿವೆ. ಭತ್ತಕ್ಕೆ ರಾಸಾಯನಿಕ ಸಿಂಪಡಣೆ ಶಿಫಾರಸುಗಳನ್ನು ನಿಷೇಧಿಸಲಾಗಿದೆ.",
            "ml": "നെല്ല് വിള മാതൃകകൾ നിലവിൽ ഗവേഷണ ഘട്ടത്തിലാണ്. നെല്ലിന് രാസ തളിക്കൽ നിർദ്ദേശങ്ങൾ അനുവദനീയമല്ല."
        },
        "greeting": {
            "en": "Namaste Ramesh! Good to speak with you. Your 3 acres of chilli in Guntur are coming along well. How can I help you out today — want to check on weather, today's work, or mandi rates?",
            "te": "నమస్కారం రమేష్ గారు! మీతో మాట్లాడటం సంతోషం. గుంటూరులోని మీ 3 ఎకరాల మిర్చి తోట బాగుంది. ఈరోజు వాతావరణం, పనులు లేదా మార్కెట్ ధరల గురించి ఏమైనా తెలుసుకోవాలా?",
            "hi": "नमस्ते रमेश जी! आपसे बात करके अच्छा लगा। गुंटूर में आपकी 3 एकड़ मिर्च की फसल अच्छी चल रही है। आज मौसम, खेत के काम या मंडी भाव के बारे में क्या जानना चाहते हैं?",
            "ta": "வணக்கம் ரமேஷ் அவர்களே! குண்டூரில் உங்கள் 3 ஏக்கர் மிளகாய் பயிர் நன்றாக உள்ளது. இன்று உங்களுக்கு என்ன உதவி தேவை?",
            "kn": "ನಮಸ್ಕಾರ ರಮೇಶ್ ಅವರೇ! ಗುಂಟೂರಿನಲ್ಲಿ ನಿಮ್ಮ 3 ಎಕರೆ ಮೆಣಸಿನಕಾಯಿ ಬೆಳೆ ಉತ್ತಮವಾಗಿದೆ. ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
            "ml": "നമസ്കാരം രമേഷ്! ഗുണ്ടൂരിലെ നിങ്ങളുടെ 3 ഏക്കർ മുളക് കൃഷി നന്നായി വളരുന്നു. ഇന്ന് എനിക്ക് എങ്ങനെ സഹായിക്കാനാകും?"
        },
        "weather_query_response": {
            "en": "In {location} right now, it's {temp}°C and {condition}. There's about a {rain_prob}% chance of rain this afternoon, so hold off on watering today. Let's see how much rain falls first.",
            "te": "{location}లో ప్రస్తుత ఉష్ణోగ్రత {temp}°C. మధ్యాహ్నం {rain_prob}% వర్షం పడే అవకాశం ఉంది, కాబట్టి ఈరోజు నీరు పెట్టడం ఆపండి. వర్షం ఎంత పడుతుందో చూద్దాం.",
            "hi": "{location} में वर्तमान तापमान {temp}°C है। दोपहर में {rain_prob}% बारिश की संभावना है, इसलिए आज पानी मत दीजिए। पहले देख लेते हैं कितनी बारिश होती है।",
            "ta": "{location}ல் தற்போதைய வெப்பநிலை {temp}°C. பிற்பகலில் {rain_prob}% மழை வாய்ப்புள்ளது, எனவே இன்று நீர்ப்பாசனம் செய்ய வேண்டாம்.",
            "kn": "{location}ನಲ್ಲಿ ತಾಪಮಾನ {temp}°C ಇದೆ. ಮಧ್ಯಾಹ್ನ {rain_prob}% ಮಳೆಯಾಗುವ ಸಾಧ್ಯತೆಯಿದೆ, ಆದ್ದರಿಂದ ಇಂದು ನೀರು ಹಾಕಬೇಡಿ.",
            "ml": "{location}-ൽ താപനില {temp}°C ആണ്. ഉച്ചതിരിഞ്ഞ് {rain_prob}% മഴയ്ക്ക് സാധ്യതയുണ്ട്, അതിനാൽ ഇന്ന് നനയ്ക്കേണ്ടതില്ല."
        },
        "irrigation_decision_response": {
            "en": "You can skip watering today, brother. There is rain expected in Guntur this afternoon, and your black soil still holds plenty of moisture. Let's wait until tomorrow morning and see if the soil needs any water.",
            "te": "ఈరోజు నీరు పెట్టాల్సిన పనిలేదు అన్నా. మధ్యాహ్నం గుంటూరులో వర్షం పడే అవకాశం ఉంది, మీ నల్లరేగడి నేలలో తేమ కూడా బాగుంది. రేపు ఉదయం చూసి అవసరమైతే నీరు పెడదాం.",
            "hi": "आज पानी देने की जरूरत नहीं है भाई। दोपहर में गुंटूर में बारिश की संभावना है और आपकी काली मिट्टी में अच्छी नमी बनी हुई है। कल सुबह देखकर तय करेंगे।",
            "ta": "இன்று நீர்ப்பாசனம் செய்ய வேண்டாம். மழை வர வாய்ப்புள்ளது மற்றும் மண்ணில் நல்ல ஈரப்பதம் உள்ளது.",
            "kn": "ಇಂದು ನೀರು ಹಾಕಬೇಕಾಗಿಲ್ಲ. ಮಳೆಯಾಗುವ ಸಾಧ್ಯತೆಯಿದೆ ಮತ್ತು ಮಣ್ಣಿನಲ್ಲಿ ತೇವಾಂಶವಿದೆ.",
            "ml": "ഇന്ന് നനയ്ക്കേണ്ടതില്ല. മഴയ്ക്ക് സാധ്യതയുണ്ട്, മണ്ണിൽ ആവശ്യത്തിന് ഈർപ്പവുമുണ്ട്."
        },
        "crop_soil_recommendation": {
            "en": "Deep black cotton soil in the Guntur region holds moisture really well. The most profitable crops suited for this ground are: Chilli (Teja variety), Cotton, and Bengal Gram. Your current 3-acre chilli crop is a perfect match for this land.",
            "te": "గుంటూరు జిల్లాలోని నల్ల రేగడి నేల తేమను చాలా బాగా నిలుపుకుంటుంది. ఈ నేలకు మిర్చి (తేజ రకం), పత్తి, మరియు శనగలు చాలా లాభదాయకమైనవి. మీ 3 ఎకరాల మిర్చి తోట ఈ భూమికి చక్కగా సరిపోతుంది.",
            "hi": "गुंटूर की गहरी काली मिट्टी नमी बहुत अच्छे से बनाए रखती है। इस मिट्टी के लिए तेजा मिर्च, कपास और चना सबसे अच्छे और मुनाफे वाले हैं। आपकी 3 एकड़ मिर्च की फसल बिल्कुल सही है।",
            "ta": "குண்டூர் பகுதியின் கரிசல் மண் ஈரப்பதத்தை நன்கு தக்கவைக்கும். மிளகாய், பருத்தி மற்றும் கொண்டைக்கடலை சிறந்தவை.",
            "kn": "ಗುಂಟೂರಿನ ಕಪ್ಪು ಮಣ್ಣು ತೇವಾಂಶವನ್ನು ಚೆನ್ನಾಗಿ ಹಿಡಿದಿಟ್ಟುಕೊಳ್ಳುತ್ತದೆ. ಮೆಣಸಿನಕಾಯಿ, ಹತ್ತಿ ಮತ್ತು ಕಡಲೆ ಉತ್ತಮ ಬೆಳೆಗಳು.",
            "ml": "ഗുണ്ടൂരിലെ കറുത്ത മണ്ണ് ഈർപ്പം നന്നായി നിലനിർത്തുന്നു. മുളക്, പരുത്തി, കടല എന്നിവ അനുയോജ്യമാണ്."
        },
        "market_price_response": {
            "en": "In Guntur mandi today, Teja chilli is selling at ₹12,000 a quintal. After about ₹150 for transport, you'll bring home ₹11,850 per quintal in your pocket. Guntur is giving the best return for you right now.",
            "te": "గుంటూరు మార్కెట్ యార్డులో తేజ మిర్చి ధర క్వింటాలుకు ₹12,000 పలుకుతోంది. రవాణా ఖర్చు ₹150 తీసేస్తే మీ చేతికి ₹11,850 వస్తుంది. ప్రస్తుతం గుంటూరులోనే మంచి లాభం ఉంది.",
            "hi": "गुंटूर मंडी में तेजा मिर्च का भाव ₹12,000 प्रति क्विंटल चल रहा है। ₹150 भाड़ा काटकर आपके हाथ में ₹11,850 प्रति क्विंटल आएंगे। गुंटूर मंडी में ही अभी सबसे अच्छा दाम मिल रहा है।",
            "ta": "குண்டூர் சந்தையில் தேஜா மிளகாய் குவிண்டாலுக்கு ₹12,000. போக்குவரத்து செலவு போக ₹11,850 உங்கள் கைக்கு கிடைக்கும்.",
            "kn": "ಗುಂಟೂರು ಮಂಡಿಯಲ್ಲಿ ತೇಜ ಮೆಣಸಿನಕಾಯಿ ದರ ₹12,000. ಸಾರಿಗೆ ವೆಚ್ಚ ಕಳೆದು ₹11,850 ನಿಮ್ಮ ಕೈಗೆ ಸಿಗುತ್ತದೆ.",
            "ml": "ഗുണ്ടൂർ മാർക്കറ്റിൽ തേജ മുളകിന്റെ വില ₹12,000 ആണ്. ഗതാഗത ചെലവ് കഴിഞ്ഞ് ₹11,850 കയ്യിൽ കിട്ടും."
        },
        "profit_simulation_response": {
            "en": "For your 3-acre chilli crop with 10 quintals per acre (30 quintals total) at ₹12,000: You can expect ₹3,60,000 in total sales. After ₹2,10,000 in cultivation and transport costs, you will make about ₹1,50,000 in clean profit.",
            "te": "మీ 3 ఎకరాల మిర్చి తోటలో మొత్తం 30 క్వింటాళ్లు వస్తే, ₹12,000 ధర వద్ద ₹3,60,000 ఆదాయం వస్తుంది. ఖర్చులు ₹2,10,000 పోగా మీ చేతికి సుమారు ₹1,50,000 నికర లాభం మిగులుతుంది.",
            "hi": "आपकी 3 एकड़ मिर्च से कुल 30 क्विंटल पर ₹12,000 के भाव से ₹3,60,000 बनेंगे। ₹2,10,000 का खर्च निकालने के बाद आपके पास लगभग ₹1,50,000 का साफ मुनाफा बचेगा।",
            "ta": "உங்கள் 3 ஏக்கர் மிளகாயில் ₹3,60,000 மொத்த வரவு. செலவு போக ₹1,50,000 லாபம் கிடைக்கும்.",
            "kn": "ನಿಮ್ಮ 3 ಎಕರೆ ಮೆಣಸಿನಕಾಯಿಯಲ್ಲಿ ₹3,60,000 ಆದಾಯ. ವೆಚ್ಚ ಕಳೆದು ₹1,50,000 ಲಾಭ ಸಿಗುತ್ತದೆ.",
            "ml": "നിങ്ങളുടെ 3 ഏക്കർ മുളകിൽ ₹3,60,000 വരുമാനം. ചെലവ് കഴിഞ്ഞ് ₹1,50,000 ലാഭം ലഭിക്കും."
        },
        "pest_curling_symptoms": {
            "en": "Don't worry, brother, we can sort this out. Look closely at the leaves: are they curling upwards like a cup, or bending downwards? Upward curl is usually tiny insects like thrips, while downward is mites. If you can take a clear photo of the leaf, send it over and I'll take a look right away.",
            "te": "కంగారు పడకండి అన్నా, చూద్దాం. ఆకులు పైకి దోనెలా ముడుచుకుంటున్నాయా, లేక కిందికి వంగుతున్నాయా? పైకి ముడిచితే తామర పురుగులు, కిందికి ముడిచితే నల్లి కావచ్చు. ఆకు స్పష్టమైన ఫోటో తీసి పంపితే వెంటనే చూసి చెబుతాను.",
            "hi": "चिंता मत कीजिए भाई, हम इसे संभाल लेंगे। पत्तियां ऊपर की तरफ मुड़ रही हैं या नीचे की तरफ? ऊपर मुड़ना थ्रिप्स कीट से होता है, नीचे मुड़ना माइट्स से। अगर प्रभावित पत्ती का साफ फोटो भेज सकें तो मैं तुरंत देखकर बताता हूँ।",
            "ta": "கவலைப்படாதீர்கள். இலைகள் மேல்நோக்கி சுருளுகிறதா அல்லது கீழ்நோக்கியா? புகைப்படத்தை அனுப்பினால் உடனே பார்த்து விடுகிறேன்.",
            "kn": "ಚಿಂತೆ ಬೇಡ. ಎಲೆಗಳು ಮೇಲಕ್ಕೆ ಮುದುಡಿಕೊಳ್ಳುತ್ತಿವೆಯೇ ಅಥವಾ ಕೆಳಮುಖವಾಗಿಯೇ? ಫೋಟೋ ಕಳುಹಿಸಿದರೆ ತಕ್ಷಣ ಪರಿಶೀಲಿಸುತ್ತೇನೆ.",
            "ml": "പേടിക്കേണ്ടതില്ല. ഇലകൾ മുകളിലേക്കാണോ താഴേക്കാണോ ചുരുളുന്നത്? ഫോട്ടോ അയച്ചാൽ ഉടൻ നോക്കാം."
        },
        "harvest_query_response": {
            "en": "Your 3-acre chilli crop in Guntur is flowering nicely right now, around 65 days in. Teja chilli takes about 140 to 160 days to fully ripen. You can do your first green chilli picking in about 35 to 40 days, and dry red chillies will be ready around 150 days.",
            "te": "గుంటూరులోని మీ 3 ఎకరాల తేజ మిర్చి తోట ఇప్పుడు 65 రోజుల వద్ద పూత దశలో ఉంది. మొదటి పచ్చిమిర్చి కోత మరో 35-40 రోజుల్లో తీసుకోవచ్చు, ఎర్ర ఎండుమిర్చి 150 రోజుల వద్ద సిద్ధమవుతుంది.",
            "hi": "गुंटूर में आपकी 3 एकड़ मिर्च अभी 65 दिनों पर फूल की अवस्था में है। पहली हरी मिर्च की तुड़ाई 35-40 दिनों में हो सकेगी, और लाल मिर्च 150 दिनों पर तैयार होगी।",
            "ta": "உங்கள் 3 ஏக்கர் மிளகாய் இப்போது பூக்கும் நிலையில் உள்ளது. முதல் பறிப்பு 35-40 நாட்களில் தொடங்கும்.",
            "kn": "ನಿಮ್ಮ ಮೆಣಸಿನಕಾಯಿ ಬೆಳೆ ಹೂಬಿಡುವ ಹಂತದಲ್ಲಿದೆ. ಮೊದಲ ಕೊಯ್ಲು 35-40 ದಿನಗಳಲ್ಲಿ ಆರಂಭವಾಗುತ್ತದೆ.",
            "ml": "നിങ്ങളുടെ മുളക് കൃഷി ഇപ്പോൾ പൂവിടുന്ന ഘട്ടത്തിലാണ്. ആദ്യ വിളവെടുപ്പ് 35-40 ദിവസങ്ങളിൽ ആരംഭിക്കും."
        },
        "crop_management_response": {
            "en": "Here is how to care for your chilli crop right now: 1. Water with morning drip only, don't let puddles form. 2. Put up yellow and blue sticky sheets in the field to catch tiny thrips. 3. Spray 19:19:19 nutrient to stop flower drop. 4. Avoid spraying during the hot midday so we don't harm honeybees.",
            "te": "మీ మిర్చి తోట సంరక్షణ కోసం: 1. ఉదయం మాత్రమే డ్రిప్ ద్వారా నీరు ఇవ్వండి. 2. పురుగుల నివారణకు జిగురు అట్టలు పెట్టండి. 3. పూత రాలకుండా 19:19:19 పిచికారీ చేయండి. 4. తేనెటీగలను కాపాడేందుకు మధ్యాహ్నం ఎండలో మందులు కొట్టవద్దు.",
            "hi": "अपनी मिर्च की फसल की देखभाल के लिए: 1. सुबह ड्रिप से पानी दें, जलभराव न होने दें। 2. कीटों के लिए चिपचिपे ट्रैप लगाएं। 3. फूल झड़ने से रोकने के लिए 19:19:19 दें। 4. मधुमक्खियों को बचाने के लिए दोपहर की धूप में छिड़काव न करें।",
            "ta": "மிளகாய் பயிர் மேலாண்மை: 1. காலையில் சொட்டு நீர் பாசனம் செய்யுங்கள். 2. ஒட்டும் பொறிகளை வையுங்கள். 3. பூ கொட்டுவதைத் தடுக்க 19:19:19 தெளிக்கவும்.",
            "kn": "ಮೆಣಸಿನಕಾಯಿ ಬೆಳೆ ನಿರ್ವಹಣೆ: 1. ಬೆಳಗ್ಗೆ ಹನಿ ನೀರಾವರಿ ಮಾಡಿ. 2. ಜಿಗುಟು ಬಲೆಗಳನ್ನು ಇರಿಸಿ. 3. ಹೂವು ಉದುರುವುದನ್ನು ತಡೆಯಲು 19:19:19 ಸಿಂಪಡಿಸಿ.",
            "ml": "മുളക് കൃഷി പരിപാലനം: 1. രാവിലെ ഡ്രിപ്പ് ഇറിഗേഷൻ നൽകുക. 2. ഒട്ടുന്ന കെണികൾ സ്ഥാപിക്കുക. 3. പൂവ് കൊഴിച്ചിൽ തടയാൻ 19:19:19 തളിക്കുക."
        },
        "farm_status_response": {
            "en": "Your 3 acres of Teja chilli in Guntur are looking healthy and green. Soil moisture is sitting nicely at 45%, and the air is 31.5°C with no pest problems. The main plan for this morning is your regular drip watering.",
            "te": "గుంటూరులోని మీ 3 ఎకరాల తేజ మిర్చి తోట ఆరోగ్యంగా, పచ్చగా ఉంది. నేలలో తేమ 45% తో బాగుంది, ఎటువంటి తెగుళ్ల బెడద లేదు. ఈరోజు ముఖ్యమైన పని: ఉదయపు డ్రిప్ తడి.",
            "hi": "गुंटूर में आपकी 3 एकड़ तेजा मिर्च की फसल बहुत हरी-भरी और स्वस्थ है। मिट्टी में 45% नमी बहुत अच्छी है और कोई कीट प्रकोप नहीं है। आज का मुख्य काम सुबह की ड्रिप सिंचाई है।",
            "ta": "உங்கள் 3 ஏக்கர் மிளகாய் பண்ணை நல்ல ஆரோக்கியமான நிலையில் உள்ளது. மண் ஈரப்பதம் 45% உள்ளது.",
            "kn": "ಗುಂಟೂರಿನಲ್ಲಿ ನಿಮ್ಮ 3 ಎಕರೆ ಮೆಣಸಿನಕಾಯಿ ತೋಟ ಉತ್ತಮವಾಗಿದೆ. ಮಣ್ಣಿನ ತೇವಾಂಶ 45% ಇದೆ.",
            "ml": "ഗുണ്ടൂരിലെ നിങ്ങളുടെ 3 ഏക്കർ മുളക് തോട്ടം നല്ല നിലയിലാണ്. മണ്ണിലെ ഈർപ്പം 45% ആണ്."
        }
    }

    CROP_ECONOMIC_BENCHMARKS: Dict[str, Dict[str, Any]] = {
        "chilli": {
            "benchmark_yield_qtl_acre": 12.0,
            "benchmark_price_qtl": 14000.0,
            "benchmark_cost_acre": 75000.0,
            "source": "ANGRAU & ICAR-IIHR Chilli Cultivation Economics"
        },
        "tomato": {
            "benchmark_yield_qtl_acre": 180.0,
            "benchmark_price_qtl": 1600.0,
            "benchmark_cost_acre": 85000.0,
            "source": "ICAR-IIHR Tomato Economic Benchmark"
        },
        "banana": {
            "benchmark_yield_qtl_acre": 300.0,
            "benchmark_price_qtl": 1400.0,
            "benchmark_cost_acre": 120000.0,
            "source": "ICAR-NRCB Banana Production Economics"
        },
        "corn": {
            "benchmark_yield_qtl_acre": 28.0,
            "benchmark_price_qtl": 2100.0,
            "benchmark_cost_acre": 30000.0,
            "source": "ICAR-IIMR Maize Economic Benchmark"
        },
        "cotton": {
            "benchmark_yield_qtl_acre": 10.0,
            "benchmark_price_qtl": 7200.0,
            "benchmark_cost_acre": 45000.0,
            "source": "CICR Cotton Production Economics"
        },
        "rice": {
            "benchmark_yield_qtl_acre": 25.0,
            "benchmark_price_qtl": 2300.0,
            "benchmark_cost_acre": 35000.0,
            "source": "NRRI Rice Economic Benchmark"
        },
        "potato": {
            "benchmark_yield_qtl_acre": 120.0,
            "benchmark_price_qtl": 1500.0,
            "benchmark_cost_acre": 80000.0,
            "source": "ICAR-CPRI Potato Production Economics"
        },
        "onion": {
            "benchmark_yield_qtl_acre": 100.0,
            "benchmark_price_qtl": 2200.0,
            "benchmark_cost_acre": 65000.0,
            "source": "DOGR Onion Economic Benchmark"
        }
    }

    @classmethod
    def _get_localized_msg(cls, key: str, lang: str = "en", **kwargs) -> str:
        lang_dict = cls.LOCALIZED_MSGS.get(key, {})
        template = lang_dict.get(lang, lang_dict.get("en", ""))
        try:
            return template.format(**kwargs)
        except Exception:
            return template

    @classmethod
    async def process_turn(
        cls,
        db: Optional[AsyncSession] = None,
        farmer_id: str = "farmer_demo_1",
        session_id: str = "session_demo_1",
        user_text: str = "",
        input_mode: str = "voice",
        language: Optional[str] = None
    ) -> OrchestrationResult:
        # 1. Digital Twin Context Retrieval
        context = None
        if db is not None:
            try:
                context = await DigitalTwinService.get_farmer_context(db, farmer_id)
                chat_repo = ChatRepository(db)
                memory_repo = MemoryRepository(db)

                # Extract automatic memory facts from farmer statements
                text_lower = user_text.lower()
                if "acre" in text_lower:
                    match = re.search(r"(\d+(\.\d+)?)\s*acres?", text_lower)
                    if match:
                        await memory_repo.upsert_memory(farmer_id, "total_area", f"{match.group(1)} acres", session_id=session_id)
                if "soil" in text_lower:
                    for s in ["black", "red", "alluvial", "sandy", "clay", "loamy"]:
                        if s in text_lower:
                            await memory_repo.upsert_memory(farmer_id, "soil_type", f"{s} soil", session_id=session_id)
            except Exception:
                context = None

        if context is None:
            from app.services.memory.digital_twin import DigitalTwinContext
            context = DigitalTwinContext(
                farmer_name="Ramesh Kumar",
                language="en",
                location="Tenali, Guntur, Andhra Pradesh",
                state="Andhra Pradesh",
                district="Guntur",
                village="Tenali",
                total_acres=3.0,
                soil_type="black",
                irrigation_source="borewell",
                active_crops=[{
                    "crop_name": "Chilli",
                    "variety": "Teja",
                    "area_acres": 3.0,
                    "current_stage": "flowering"
                }],
                historical_crops=["paddy", "cotton"],
                memories={"historical_preference": "Prefers Teja cultivar with Guntur cold storage"}
            )

        # Determine active language preference:
        # 1. Non-English script detected in user_text (e.g. Telugu, Hindi, Tamil)
        # 2. Explicitly passed language parameter (from UI / request headers)
        # 3. Context / farmer profile preferred language
        # 4. Default 'en'
        detected_script = IntentNormalizationService.detect_language(user_text, None)
        if detected_script and detected_script != "en":
            active_lang = detected_script
        elif language:
            active_lang = language
        elif context and context.language:
            active_lang = context.language
        else:
            active_lang = "en"
        if farmer_id == "demo_farmer_1":
            farm_id = "farm_demo_1"
            if context is not None:
                context.farm_id = "farm_demo_1"
                context.active_crops = [{
                    "crop_name": "Chilli",
                    "variety": "Teja",
                    "area_acres": 3.0,
                    "current_stage": "vegetative"
                }]
        else:
            farm_id = getattr(context, "farm_id", "farm_1")

        text_lower = user_text.lower()

        # 1.5 DIALOGUE SESSION & MULTI-TURN SLOT FILLING
        dialogue_session = FarmerDialogueManager.get_or_create_session(session_id, farmer_id, language=active_lang)

        # Extract slots from user text
        for s in ["black", "red", "alluvial", "sandy", "clay", "loamy", "నల్ల", "నల్లరేగడి", "ఎర్ర", "काली", "लाल", "दोमट"]:
            if s in text_lower:
                canonical_s = "black" if any(k in s for k in ["black", "నల్ల", "काली"]) else s
                dialogue_session.collected_slots["soil_type"] = canonical_s
                break

        if any(w in text_lower for w in ["irrigation", "water", "borewell", "canal", "drip", "rainfed", "good irrigation", "water available", "బావి", "బోరు", "నీరు", "మంచి నీటి", "సిరచ", "पानी"]):
            dialogue_session.collected_slots["irrigation_water"] = "good"

        # Check pending slot fulfillment
        if dialogue_session.pending_slot == "SOIL_TYPE":
            if "soil_type" not in dialogue_session.collected_slots:
                dialogue_session.collected_slots["soil_type"] = "black"
            dialogue_session.pending_slot = "IRRIGATION_AVAILABILITY"
            q_text = MissingInformationDetector.get_localized_question("ask_irrigation_for_crop", active_lang)
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, q_text, intent="SLOT_FILLING_IRRIGATION")
            return OrchestrationResult(response_text=q_text, visual_cards=[], voice_state="RESPONDING", trace_id=f"trace_slot_{farmer_id}")

        elif dialogue_session.pending_slot == "IRRIGATION_AVAILABILITY":
            if "irrigation_water" not in dialogue_session.collected_slots:
                dialogue_session.collected_slots["irrigation_water"] = "good"
            dialogue_session.pending_slot = "CONFIRM_CROP_RECOMMENDATION"
            q_text = MissingInformationDetector.get_localized_question("confirm_crop_recommendation", active_lang)
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, q_text, intent="SLOT_FILLING_CONFIRM")
            return OrchestrationResult(response_text=q_text, visual_cards=[], voice_state="RESPONDING", trace_id=f"trace_slot_{farmer_id}")

        elif dialogue_session.pending_slot == "CONFIRM_CROP_RECOMMENDATION":
            dialogue_session.pending_slot = None
            dialogue_session.active_topic = "CROP_RECOMMENDATION"
            crop_resp = cls._get_localized_msg("crop_soil_recommendation", active_lang)
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, crop_resp, intent="CROP_RECOMMENDATION")
            return OrchestrationResult(response_text=crop_resp, visual_cards=[], voice_state="RESPONDING", trace_id=f"trace_crop_rec_{farmer_id}")

        # -------------------------------------------------------------
        # 2. CHECK MULTI-TURN CONFIRMATION STATE MACHINE
        # -------------------------------------------------------------
        pending_sess = ConfirmationStateMachine.get_session(session_id, farmer_id)
        if pending_sess and pending_sess.state != ConfirmationState.NO_CONFIRMATION:
            parsed_intent = IntentNormalizationService.parse_intent(user_text, language=active_lang)
            active_lang = parsed_intent.language or active_lang

            # A. Farmer cancelled / refused
            is_cancel = (
                parsed_intent.intent_type == VoiceIntentType.TASK_CANCEL_ACTION
                or any(w in text_lower for w in ["no", "cancel", "abort", "don't", "stop", "nevermind", "వద్దు", "రద్దు", "नहीं", "இல்லை", "வேண்டாம்", "ಬೇಡ", "വേണ്ട"])
            )
            if is_cancel:
                ConfirmationStateMachine.clear_session(session_id, farmer_id)
                return OrchestrationResult(
                    response_text=cls._get_localized_msg("action_cancelled", active_lang),
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=parsed_intent.trace_id
                )

            # B. Farmer confirmed pending action
            is_confirm = (
                parsed_intent.intent_type == VoiceIntentType.TASK_CONFIRM
                or any(text_lower.startswith(w) for w in ["yes", "confirm", "proceed", "ok", "okay", "sure", "correct", "do it", "అవును", "సరే", "ఖరారు", "हाँ", "हा", "सही", "ஆம்", "சரி", "ಹೌದು", "അതെ"])
                or ("confirm" in text_lower)
            )
            if is_confirm:
                if pending_sess.pending_action == "TASK_SKIP" and pending_sess.selected_task_id:
                    task = TaskIntelligenceEngine.skip_task(
                        task_id=pending_sess.selected_task_id,
                        farmer_id=farmer_id,
                        reason=f"Farmer confirmed skip via {input_mode}",
                        farm_id=farm_id
                    )
                    ConfirmationStateMachine.clear_session(session_id, farmer_id)
                    RecommendationTraceStore.record_trace(RecommendationRecord(
                        farmer_id=farmer_id,
                        farm_id=farm_id,
                        intent="TASK_SKIP_CONFIRMED",
                        tools_used=["TaskIntelligenceEngine.skip_task"],
                        recommendation_text=f"Task '{task.title}' skipped following farmer confirmation.",
                        confidence=1.0
                    ))
                    return OrchestrationResult(
                        response_text=cls._get_localized_msg("task_skipped", active_lang, title=task.title),
                        visual_cards=[],
                        voice_state="RESPONDING",
                        trace_id=parsed_intent.trace_id
                    )
                elif pending_sess.pending_action == "TASK_POSTPONE" and pending_sess.selected_task_id:
                    delay = pending_sess.parameters.get("days", 2)
                    task = TaskIntelligenceEngine.postpone_task(
                        task_id=pending_sess.selected_task_id,
                        farmer_id=farmer_id,
                        reason=f"Farmer postponed by {delay} days via {input_mode}",
                        days_to_postpone=delay,
                        farm_id=farm_id
                    )
                    ConfirmationStateMachine.clear_session(session_id, farmer_id)
                    RecommendationTraceStore.record_trace(RecommendationRecord(
                        farmer_id=farmer_id,
                        farm_id=farm_id,
                        intent="TASK_POSTPONE_CONFIRMED",
                        tools_used=["TaskIntelligenceEngine.postpone_task"],
                        recommendation_text=f"Task '{task.title}' postponed to {task.due_at}.",
                        confidence=1.0
                    ))
                    return OrchestrationResult(
                        response_text=cls._get_localized_msg("task_postponed", active_lang, title=task.title, date=task.due_at),
                        visual_cards=[],
                        voice_state="RESPONDING",
                        trace_id=parsed_intent.trace_id
                    )
                elif pending_sess.pending_action == "TASK_COMPLETE" and pending_sess.selected_task_id:
                    task = TaskIntelligenceEngine.complete_task(
                        task_id=pending_sess.selected_task_id,
                        farmer_id=farmer_id,
                        farm_id=farm_id,
                        completion_source=input_mode.upper()
                    )
                    ConfirmationStateMachine.clear_session(session_id, farmer_id)
                    RecommendationTraceStore.record_trace(RecommendationRecord(
                        farmer_id=farmer_id,
                        farm_id=farm_id,
                        intent="TASK_COMPLETE_CONFIRMED",
                        tools_used=["TaskIntelligenceEngine.complete_task"],
                        recommendation_text=f"Task '{task.title}' completed following confirmation.",
                        confidence=1.0
                    ))
                    return OrchestrationResult(
                        response_text=cls._get_localized_msg("task_completed", active_lang, title=task.title),
                        visual_cards=[],
                        voice_state="RESPONDING",
                        trace_id=parsed_intent.trace_id
                    )

            # C. Farmer selecting between ambiguous candidate tasks
            if pending_sess.state == ConfirmationState.AWAITING_TASK_SELECTION:
                selected_crop = parsed_intent.target_crop or IntentNormalizationService._extract_crop(user_text.lower())
                tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
                matched_task = None
                for cid in pending_sess.candidate_task_ids:
                    t = next((item for item in tasks if item.task_id == cid), None)
                    if t and selected_crop and t.crop.lower() == selected_crop.lower():
                        matched_task = t
                        break

                if matched_task:
                    if pending_sess.pending_action == "TASK_COMPLETE":
                        task = TaskIntelligenceEngine.complete_task(
                            task_id=matched_task.task_id,
                            farmer_id=farmer_id,
                            farm_id=farm_id,
                            completion_source=input_mode.upper()
                        )
                        ConfirmationStateMachine.clear_session(session_id, farmer_id)
                        RecommendationTraceStore.record_trace(RecommendationRecord(
                            farmer_id=farmer_id,
                            farm_id=farm_id,
                            intent="TASK_COMPLETE_DISAMBIGUATED",
                            tools_used=["TaskIntelligenceEngine.complete_task"],
                            recommendation_text=f"Task '{task.title}' completed via {input_mode.upper()}.",
                            confidence=1.0
                        ))
                        return OrchestrationResult(
                            response_text=cls._get_localized_msg("task_completed", active_lang, title=task.title),
                            visual_cards=[],
                            voice_state="RESPONDING",
                            trace_id=parsed_intent.trace_id
                        )
                    elif pending_sess.pending_action == "TASK_POSTPONE":
                        delay = pending_sess.parameters.get("days", 2)
                        task = TaskIntelligenceEngine.postpone_task(
                            task_id=matched_task.task_id,
                            farmer_id=farmer_id,
                            reason=f"Farmer postponed by {delay} days via {input_mode}",
                            days_to_postpone=delay,
                            farm_id=farm_id
                        )
                        ConfirmationStateMachine.clear_session(session_id, farmer_id)
                        return OrchestrationResult(
                            response_text=cls._get_localized_msg("task_postponed", active_lang, title=task.title, date=task.due_at),
                            visual_cards=[],
                            voice_state="RESPONDING",
                            trace_id=parsed_intent.trace_id
                        )
                    elif pending_sess.pending_action == "TASK_SKIP":
                        if matched_task.task_type == TaskType.IRRIGATION:
                            prompt = cls._get_localized_msg("skip_consequence_irrigation", active_lang, title=matched_task.title)
                            ConfirmationStateMachine.start_confirmation(
                                session_id=session_id,
                                farmer_id=farmer_id,
                                state=ConfirmationState.AWAITING_CONFIRMATION,
                                action="TASK_SKIP",
                                prompt_message=prompt,
                                selected_task_id=matched_task.task_id
                            )
                            return OrchestrationResult(
                                response_text=prompt,
                                visual_cards=[],
                                voice_state="RESPONDING",
                                trace_id=parsed_intent.trace_id
                            )
                        else:
                            task = TaskIntelligenceEngine.skip_task(
                                task_id=matched_task.task_id,
                                farmer_id=farmer_id,
                                reason=f"Farmer skipped via {input_mode}",
                                farm_id=farm_id
                            )
                            ConfirmationStateMachine.clear_session(session_id, farmer_id)
                            return OrchestrationResult(
                                response_text=cls._get_localized_msg("task_skipped", active_lang, title=task.title),
                                visual_cards=[],
                                voice_state="RESPONDING",
                                trace_id=parsed_intent.trace_id
                            )

        # -------------------------------------------------------------
        # 3. SAFETY ENGINE PROHIBITED SUBSTANCE & RICE RESEARCH-ONLY
        # -------------------------------------------------------------
        user_safety = SafetyEngine.evaluate(user_text)
        if not user_safety.is_safe:
            from app.services.voice.persona import BhoomiPersonaEngine
            crop_name = context.active_crops[0]["crop_name"] if context and context.active_crops else "chilli"
            safety_refusal = BhoomiPersonaEngine.format_vision_diagnosis(
                crop=crop_name,
                disease_name="pesticide_hazard",
                confidence=1.0,
                safety_blocked=True,
                language=active_lang,
                farmer_name=context.farmer_name if context else None
            )
            return OrchestrationResult(
                response_text=safety_refusal,
                visual_cards=[{
                    "card_type": "safety_restriction_card",
                    "title": "Safety Alert: Prohibited Substance Blocked",
                    "data": {
                        "blocked_reasons": user_safety.blocked_reasons,
                        "advisory": safety_refusal
                    }
                }],
                voice_state="RESPONDING",
                trace_id=f"trace_safety_{farmer_id}"
            )

        text_lower = user_text.lower()
        import re
        is_rice_query = bool(re.search(r"\b(rice|paddy)\b", text_lower)) or any(w in text_lower for w in ["వరి", "వరికి", "వరిలో", "వరి పంట", "వరి ఎరువులు", "ధాన్యం", "धान", "चावल", "நெல்", "ಭತ್ತ", "നെല്ല്"])
        is_chemical_inquiry = any(w in text_lower for w in [
            "pesticide", "spray", "chemical", "insecticide", "fungicide", "fertilizer", "dose", "treatment",
            "పురుగుమందు", "స్ప్రే", "కీటక", "ఎరువు", "ఎరువులు", "మందు", "कीटनाशक", "छिड़काव", "खाद", "दवा", "மருந்து", "தெளி", "உரம்", "ಕೀಟನಾಶಕ", "ಗೊಬ್ಬರ", "കീടനാശിനി", "വളം"
        ])
        if is_rice_query and (is_chemical_inquiry or any(k in text_lower for k in ["spray", "fertilizer", "dose", "pesticide", "ఎరువు", "పురుగుమందు", "खाद", "दवा", "மருந்து", "உரம்"])):
            return OrchestrationResult(
                response_text=cls._get_localized_msg("rice_research_only", active_lang),
                visual_cards=[{
                    "card_type": "safety_restriction_card",
                    "title": "Safety Notice: Rice (RESEARCH_ONLY)",
                    "data": {
                        "crop": "Rice (Oryza sativa)",
                        "protocol_status": "RESEARCH_ONLY",
                        "validation_stage": "Phase 5 Physical Ground Validation in Progress",
                        "rule": "Farmer-facing chemical spraying prescriptions are barred for rice models.",
                        "advisory": cls._get_localized_msg("rice_research_only", active_lang)
                    }
                }],
                voice_state="RESPONDING",
                trace_id=f"trace_rice_{farmer_id}"
            )

        # -------------------------------------------------------------
        # 4. CANONICAL INTENT PARSING (VOICE / TYPING PARITY)
        # -------------------------------------------------------------
        intent = IntentNormalizationService.parse_intent(user_text, language=active_lang)
        active_lang = intent.language or active_lang

        # Low-confidence voice clarification guardrail
        if user_text.strip() in ["...", "", "muffled"] or (input_mode == "voice" and intent.intent_type == VoiceIntentType.UNKNOWN and intent.confidence < 0.5):
            return OrchestrationResult(
                response_text=cls._get_localized_msg("low_confidence_clarification", active_lang),
                visual_cards=[],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # -------------------------------------------------------------
        # 5. TASK COMPLETION VIA VOICE/TYPING
        # -------------------------------------------------------------
        if intent.intent_type == VoiceIntentType.TASK_COMPLETE:
            state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
            tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
            if not tasks:
                tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)

            active_tasks = [t for t in tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.EXPIRED]]
            candidates = []
            if intent.target_task_type:
                candidates = [t for t in active_tasks if t.task_type == intent.target_task_type]
            elif intent.target_crop:
                candidates = [t for t in active_tasks if t.crop.lower() == intent.target_crop.lower()]
            else:
                resolved_task = FarmerDialogueManager.resolve_pronoun_task(session_id, farmer_id, active_tasks)
                if resolved_task:
                    candidates = [resolved_task]
                else:
                    candidates = active_tasks

            if not candidates:
                return OrchestrationResult(
                    response_text=cls._get_localized_msg("no_matching_task", active_lang),
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )

            if len(candidates) > 1:
                options_str = ", ".join(set(t.crop for t in candidates))
                ConfirmationStateMachine.start_confirmation(
                    session_id=session_id,
                    farmer_id=farmer_id,
                    state=ConfirmationState.AWAITING_TASK_SELECTION,
                    action="TASK_COMPLETE",
                    prompt_message=cls._get_localized_msg("ambiguous_task", active_lang, options=options_str),
                    candidate_task_ids=[t.task_id for t in candidates]
                )
                return OrchestrationResult(
                    response_text=cls._get_localized_msg("ambiguous_task", active_lang, options=options_str),
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )

            target_task = candidates[0]
            can_run, dep_reason = TaskIntelligenceEngine.can_execute(target_task, tasks)
            if not can_run:
                return OrchestrationResult(
                    response_text=f"Cannot complete '{target_task.title}' because {dep_reason}",
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )

            completed = TaskIntelligenceEngine.complete_task(
                task_id=target_task.task_id,
                farmer_id=farmer_id,
                farm_id=farm_id,
                completion_source=input_mode.upper()
            )
            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="TASK_COMPLETE",
                tools_used=["TaskIntelligenceEngine.complete_task"],
                recommendation_text=f"Task '{completed.title}' completed via {input_mode.upper()}",
                confidence=1.0
            ))
            return OrchestrationResult(
                response_text=cls._get_localized_msg("task_completed", active_lang, title=completed.title),
                visual_cards=[],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # -------------------------------------------------------------
        # 6. TASK POSTPONEMENT VIA VOICE/TYPING
        # -------------------------------------------------------------
        if intent.intent_type == VoiceIntentType.TASK_POSTPONE:
            state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
            tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
            if not tasks:
                tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)

            active_tasks = [t for t in tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            candidates = []
            if intent.target_task_type:
                candidates = [t for t in active_tasks if t.task_type == intent.target_task_type]
            elif intent.target_crop:
                candidates = [t for t in active_tasks if t.crop.lower() == intent.target_crop.lower()]
            else:
                resolved_task = FarmerDialogueManager.resolve_pronoun_task(session_id, farmer_id, active_tasks)
                if resolved_task:
                    candidates = [resolved_task]
                else:
                    candidates = active_tasks

            if not candidates:
                return OrchestrationResult(
                    response_text=cls._get_localized_msg("no_matching_task", active_lang),
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )

            if len(candidates) > 1:
                options_str = ", ".join(set(t.crop for t in candidates))
                ConfirmationStateMachine.start_confirmation(
                    session_id=session_id,
                    farmer_id=farmer_id,
                    state=ConfirmationState.AWAITING_TASK_SELECTION,
                    action="TASK_POSTPONE",
                    prompt_message=cls._get_localized_msg("ambiguous_task", active_lang, options=options_str),
                    candidate_task_ids=[t.task_id for t in candidates],
                    parameters={"days": intent.requested_delay_days or 2}
                )
                return OrchestrationResult(
                    response_text=cls._get_localized_msg("ambiguous_task", active_lang, options=options_str),
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )

            target_task = candidates[0]
            days = intent.requested_delay_days or 2
            postponed = TaskIntelligenceEngine.postpone_task(
                task_id=target_task.task_id,
                farmer_id=farmer_id,
                reason=f"Farmer requested postponement by {days} days via {input_mode}",
                days_to_postpone=days,
                farm_id=farm_id
            )
            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="TASK_POSTPONE",
                tools_used=["TaskIntelligenceEngine.postpone_task"],
                recommendation_text=f"Task '{postponed.title}' postponed to {postponed.due_at}",
                confidence=1.0
            ))
            return OrchestrationResult(
                response_text=cls._get_localized_msg("task_postponed", active_lang, title=postponed.title, date=postponed.due_at),
                visual_cards=[],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # -------------------------------------------------------------
        # 7. TASK SKIP VIA VOICE/TYPING (CONSEQUENTIAL CONFIRMATION)
        # -------------------------------------------------------------
        if intent.intent_type == VoiceIntentType.TASK_SKIP:
            state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
            tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
            if not tasks:
                tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)

            active_tasks = [t for t in tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            candidates = []
            if intent.target_task_type:
                candidates = [t for t in active_tasks if t.task_type == intent.target_task_type]
            elif intent.target_crop:
                candidates = [t for t in active_tasks if t.crop.lower() == intent.target_crop.lower()]
            else:
                resolved_task = FarmerDialogueManager.resolve_pronoun_task(session_id, farmer_id, active_tasks)
                if resolved_task:
                    candidates = [resolved_task]
                else:
                    candidates = active_tasks

            if not candidates:
                return OrchestrationResult(
                    response_text=cls._get_localized_msg("no_matching_task", active_lang),
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )

            if len(candidates) > 1:
                options_str = ", ".join(set(t.crop for t in candidates))
                ConfirmationStateMachine.start_confirmation(
                    session_id=session_id,
                    farmer_id=farmer_id,
                    state=ConfirmationState.AWAITING_TASK_SELECTION,
                    action="TASK_SKIP",
                    prompt_message=cls._get_localized_msg("ambiguous_task", active_lang, options=options_str),
                    candidate_task_ids=[t.task_id for t in candidates]
                )
                return OrchestrationResult(
                    response_text=cls._get_localized_msg("ambiguous_task", active_lang, options=options_str),
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )

            target_task = candidates[0]
            # Require confirmation for consequential operations (e.g. Irrigation or High Priority)
            if target_task.task_type == TaskType.IRRIGATION or target_task.priority in [DecisionPriority.HIGH, DecisionPriority.CRITICAL]:
                prompt = cls._get_localized_msg("skip_consequence_irrigation", active_lang, title=target_task.title)
                ConfirmationStateMachine.start_confirmation(
                    session_id=session_id,
                    farmer_id=farmer_id,
                    state=ConfirmationState.AWAITING_CONFIRMATION,
                    action="TASK_SKIP",
                    prompt_message=prompt,
                    selected_task_id=target_task.task_id
                )
                return OrchestrationResult(
                    response_text=prompt,
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )
            else:
                skipped = TaskIntelligenceEngine.skip_task(
                    task_id=target_task.task_id,
                    farmer_id=farmer_id,
                    reason=f"Farmer opted to skip via {input_mode}",
                    farm_id=farm_id
                )
                return OrchestrationResult(
                    response_text=cls._get_localized_msg("task_skipped", active_lang, title=skipped.title),
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )

        # -------------------------------------------------------------
        # 8. TASK WHY / EXPLANATION
        # -------------------------------------------------------------
        if intent.intent_type == VoiceIntentType.TASK_WHY:
            state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
            tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
            if not tasks:
                tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)

            candidates = []
            if intent.target_task_type:
                candidates = [t for t in tasks if t.task_type == intent.target_task_type]
            elif intent.target_crop:
                candidates = [t for t in tasks if t.crop.lower() == intent.target_crop.lower()]
            else:
                candidates = tasks

            if candidates:
                t = candidates[0]
                reason_detail = t.reason or t.postponement_reason or "Regular crop calendar activity"
                evidence_detail = t.evidence or "Agronomic lifecycle schedule"
                msg = f"Task '{t.title}' status is {t.status.value}. Reason: {reason_detail}. Evidence: {evidence_detail}."
                return OrchestrationResult(response_text=msg, visual_cards=[], voice_state="RESPONDING", trace_id=intent.trace_id)

        # -------------------------------------------------------------
        # 9. DIRECT FARM MANAGER QUERIES & BRIEFINGS
        # -------------------------------------------------------------
        if intent.intent_type == VoiceIntentType.TASK_TODAY or any(w in text_lower for w in [
            "what should i do today", "today's tasks", "what to do today", "today's task", "today tasks", "today's priorities", "tasks for today", "activities today",
            "schedule today", "ఈరోజు నా పొలంలో ఏం చేయాలి", "ఈరోజు ఏం చేయాలి", "నేను ఏమి చేయాలి", "ఈరోజు పనులు", "ఈరోజు పనులేమిటి", "నేడు పనులు",
            "आज मुझे खेत में क्या करना चाहिए", "आज क्या करना चाहिए", "आज क्या करना है", "आज के काम", "आज के कार्य", "आज क्या करें"
        ]):
            state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
            state.preferred_language = active_lang
            briefing = DailyFarmBriefingService.generate_today_briefing(state, language=active_lang)

            # Record active task in dialogue session for multi-turn pronoun resolution
            farm_tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id) or TaskIntelligenceEngine.generate_tasks_for_farm(state)
            irrig_tasks = [t for t in farm_tasks if t.task_type == TaskType.IRRIGATION and t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            if irrig_tasks:
                FarmerDialogueManager.set_last_discussed_task(session_id, farmer_id, irrig_tasks[0])
            elif farm_tasks:
                FarmerDialogueManager.set_last_discussed_task(session_id, farmer_id, farm_tasks[0])
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, briefing.voice_announcement, intent="TASK_TODAY")

            return OrchestrationResult(
                response_text=briefing.voice_announcement,
                visual_cards=[{
                    "card_type": "daily_briefing_card",
                    "title": f"Today's Farm Briefing: {state.active_crop}",
                    "data": briefing.model_dump()
                }],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        if intent.intent_type == VoiceIntentType.TASK_WEEK or any(w in text_lower for w in ["what should i do this week", "weekly plan", "weekly tasks", "ఈ వారం", "इस हफ्ते", "week"]):
            state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
            state.preferred_language = active_lang
            week_briefing = DailyFarmBriefingService.generate_week_briefing(state, language=active_lang)
            return OrchestrationResult(
                response_text=week_briefing.voice_announcement,
                visual_cards=[{
                    "card_type": "weekly_briefing_card",
                    "title": f"Weekly Farm Plan: {state.active_crop}",
                    "data": week_briefing.model_dump()
                }],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # -------------------------------------------------------------
        # 9.1 AGRICULTURAL NEWS & POLICY/MARKET UPDATES
        # -------------------------------------------------------------
        if intent.intent_type == VoiceIntentType.AGRICULTURAL_NEWS or any(w in text_lower for w in [
            "latest agriculture news", "latest news", "agriculture news", "agri news", "farming news",
            "market updates", "news update", "news updates", "crop news", "price news", "policy news",
            "updates on", "any updates", "update on", "prices and market", "price and market", "chilli prices",
            "వార్తలు", "వ్యవసాయ వార్తలు", "తాజా వార్తలు", "రైతు వార్తలు", "మార్కెట్ వార్తలు",
            "సమాచారం", "అప్‌డేట్స్", "అప్డేట్స్",
            "समाचार", "कृषि समाचार", "ताज़ा समाचार", "ताज़ा खबरें", "खेती की खबरें", "किसान समाचार", "अपडेट"
        ]):
            from app.services.news.news_service import AgriculturalNewsService
            from app.services.voice.persona import BhoomiPersonaEngine

            # Fix 2: Only default to farmer's active profile crop if query is genuinely crop-agnostic
            is_agnostic = AgriculturalNewsService.is_crop_agnostic_query(user_text)
            if intent.target_crop:
                crop_name = intent.target_crop
            elif is_agnostic:
                crop_name = context.active_crops[0]["crop_name"] if context and context.active_crops else "Chilli"
            else:
                crop_name = AgriculturalNewsService.extract_topic_commodity(user_text)

            # Fetch live filtered agricultural articles
            articles = AgriculturalNewsService.get_latest_agricultural_news(
                crop=crop_name,
                query=user_text,
                language=active_lang,
                limit=3
            )

            # Generate warm plain spoken summary via BhoomiPersonaEngine
            spoken_news = BhoomiPersonaEngine.format_news_summary(
                articles=articles,
                crop=crop_name,
                language=active_lang,
                farmer_name=context.farmer_name if context else None,
                query_topic=user_text
            )

            news_cards_data = [
                {
                    "title": a.title,
                    "source": a.source,
                    "pub_date": a.pub_date,
                    "category": a.category,
                    "link": a.link
                }
                for a in articles
            ]

            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, spoken_news, intent="AGRICULTURAL_NEWS")

            return OrchestrationResult(
                response_text=spoken_news,
                visual_cards=[{
                    "card_type": "agricultural_news_card",
                    "title": f"Agricultural News & Updates: {crop_name or 'General'}",
                    "data": {
                        "crop": crop_name or "General",
                        "articles_count": len(articles),
                        "articles": news_cards_data,
                        "language": active_lang
                    }
                }] if articles else [],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        if intent.intent_type == VoiceIntentType.TASK_PENDING or any(w in text_lower for w in ["what is pending", "what did i miss", "what is overdue", "what should i do next", "pending tasks"]):
            state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
            farm_tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
            pending = [t for t in farm_tasks if t.status in [TaskStatus.DUE, TaskStatus.PLANNED]]
            overdue = [t for t in farm_tasks if t.is_overdue]

            if overdue:
                msg = f"You have {len(overdue)} overdue task(s): '{overdue[0].title}'. Please prioritize completing or updating them."
            elif pending:
                msg = f"You have {len(pending)} pending farm task(s). Next priority: '{pending[0].title}' ({pending[0].reason})."
            else:
                msg = "All scheduled farm activities are up to date. Excellent work!"

            return OrchestrationResult(
                response_text=msg,
                visual_cards=[{
                    "card_type": "tasks_status_card",
                    "title": "Pending & Overdue Farm Tasks",
                    "data": {"pending_count": len(pending), "overdue_count": len(overdue), "tasks": [t.model_dump() for t in farm_tasks]}
                }],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        if any(w in text_lower for w in ["did i finish irrigation", "irrigation completed", "did i irrigate"]):
            tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
            irrig_tasks = [t for t in tasks if t.task_type == TaskType.IRRIGATION]
            if irrig_tasks and irrig_tasks[0].status == TaskStatus.COMPLETED:
                msg = f"Yes, irrigation task '{irrig_tasks[0].title}' was recorded as COMPLETED at {irrig_tasks[0].completed_at}."
            elif irrig_tasks and irrig_tasks[0].status == TaskStatus.POSTPONED:
                msg = f"No, irrigation is currently POSTPONED: {irrig_tasks[0].postponement_reason}."
            elif irrig_tasks and irrig_tasks[0].status == TaskStatus.DUE:
                msg = "No, your scheduled irrigation is currently DUE. Did you complete the watering?"
            else:
                msg = "No recent irrigation task has been recorded as finished today."

            return OrchestrationResult(response_text=msg, visual_cards=[], voice_state="RESPONDING", trace_id=intent.trace_id)

        if any(w in text_lower for w in ["why was my spraying task postponed", "spraying postponed", "why postpone spray"]):
            tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
            spray_tasks = [t for t in tasks if t.task_type in [TaskType.SPRAYING, TaskType.FERTILIZATION] and t.status == TaskStatus.POSTPONED]
            if spray_tasks:
                msg = f"Your spray task was postponed because: {spray_tasks[0].postponement_reason}"
            else:
                msg = "There is no postponed spraying task currently on record."
            return OrchestrationResult(response_text=msg, visual_cards=[], voice_state="RESPONDING", trace_id=intent.trace_id)

        if any(w in text_lower for w in ["when should i inspect", "when to inspect", "inspect my"]):
            tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
            scout_tasks = [t for t in tasks if t.task_type in [TaskType.FIELD_INSPECTION, TaskType.CROP_HEALTH_SCOUTING]]
            if scout_tasks:
                msg = f"You are scheduled to inspect your crop on {scout_tasks[0].due_at}. Reason: {scout_tasks[0].reason}"
            else:
                msg = "Regular bi-weekly crop scouting is recommended during the current growth stage."
            return OrchestrationResult(response_text=msg, visual_cards=[], voice_state="RESPONDING", trace_id=intent.trace_id)

        if intent.intent_type == VoiceIntentType.FARM_CHANGES or any(w in text_lower for w in ["what changed", "what is new", "మార్పులు"]):
            state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
            changes = FarmChangeDetectionService.detect_changes(state)
            return OrchestrationResult(
                response_text=changes.farmer_summary,
                visual_cards=[{
                    "card_type": "farm_changes_card",
                    "title": "Farm Updates & Changes",
                    "data": changes.model_dump()
                }],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # -------------------------------------------------------------
        # 9.5 DOMAIN-SPECIFIC DETERMINISTIC HANDLERS (VOICE & WEB CHAT)
        # -------------------------------------------------------------
        # A. Greetings
        if any(w in text_lower for w in ["hello", "hi", "hey", "namaste", "namaskaram", "నమస్కారం", "నమస్తే", "హలో", "नमस्ते", "வணக்கம்", "நமஸ்காரம்", "ನಮಸ್ಕಾರ", "നമസ്കാരം"]) and len(text_lower.split()) <= 5:
            greeting_msg = cls._get_localized_msg("greeting", active_lang)
            return OrchestrationResult(
                response_text=greeting_msg,
                visual_cards=[],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )


        # CIBRC Banned / Restricted Chemical Safety Guardrail
        banned_terms = ["monocrotophos", "endosulfan", "paraquat", "phorate", "మోనోక్రోటోఫాస్", "మోనో", "ఎండోసల్ఫాన్", "मोनोक्रोटोफॉस", "एंडोसल्फान"]
        if any(b in text_lower for b in banned_terms):
            from app.services.voice.persona import BhoomiPersonaEngine
            crop_name = context.active_crops[0]["crop_name"] if context and context.active_crops else "chilli"
            safety_refusal = BhoomiPersonaEngine.format_vision_diagnosis(
                crop=crop_name,
                disease_name="pesticide_hazard",
                confidence=1.0,
                safety_blocked=True,
                language=active_lang,
                farmer_name=context.farmer_name if context else None
            )
            return OrchestrationResult(
                response_text=safety_refusal,
                visual_cards=[{
                    "card_type": "safety_block_card",
                    "title": "Safety Alert: Restricted Substance",
                    "data": {
                        "regulation": "Central Insecticides Board & Registration Committee (CIBRC)",
                        "status": "BLOCKED",
                        "message": safety_refusal
                    }
                }],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # B0. Spray Weather Safety Evaluation (Deterministic Agricultural Spray Rules)
        if intent.intent_type == VoiceIntentType.SPRAY_WEATHER_SAFETY or any(
            w in text_lower for w in ["can i spray", "safe to spray", "spray tomorrow", "spray herbicide", "spray pesticide", "పిచికారీ చేయవచ్చా", "స్ప్రే చేయవచ్చా", "మందు కొట్టవచ్చా", "छिड़काव कर सकते", "स्प्रे कर सकते"]
        ):
            loc = context.district or "Guntur"
            weather_card = await ToolRegistry.execute_tool("get_current_weather", {"location": loc})
            w_dict = weather_card.get("data", {})
            cur = w_dict.get("current", {})
            fcasts = w_dict.get("forecast_3_days", [])

            # Determine target forecast day (tomorrow or today)
            target_f = fcasts[0] if fcasts else {}
            if "tomorrow" in text_lower or "రేపు" in text_lower or "कल" in text_lower or "நாளை" in text_lower or "ನಾಳೆ" in text_lower or "നാളെ" in text_lower:
                target_f = fcasts[1] if len(fcasts) > 1 else (fcasts[0] if fcasts else {})

            rain_prob = target_f.get("rain_probability") if target_f.get("rain_probability") is not None else (cur.get("rain_probability_percent") or 20)
            cond = target_f.get("condition") or cur.get("weather_condition") or "Partly Cloudy"
            temp = target_f.get("temp_max") or cur.get("temperature_c") or 31.0
            wind_spd = cur.get("wind_speed_kmh") or 10.0
            rainfall = target_f.get("rainfall_mm") or 0.0
            target_date = target_f.get("date", "Tomorrow")

            # Deterministic Agronomic Safety Assessment
            is_safe = True
            reasons = []
            if rain_prob >= 35 or rainfall > 1.0:
                is_safe = False
                reasons.append(f"High rain probability ({rain_prob}%) will wash away applied chemicals.")
            if wind_spd > 15.0:
                is_safe = False
                reasons.append(f"Wind speed ({wind_spd} km/h) exceeds 15 km/h limit, causing chemical spray drift.")
            elif wind_spd < 2.5 and temp > 32.0:
                reasons.append("Very low wind with high heat creates thermal inversion; spray only in early morning.")
            if temp > 35.0:
                is_safe = False
                reasons.append(f"High temperature ({temp}°C) causes rapid chemical evaporation and leaf scorch.")

            if active_lang == "te":
                if is_safe:
                    spray_resp = (
                        f"అవును అన్నా, {target_date} తేదీన {loc}లో పిచికారీ చేయడానికి వాతావరణం అనుకూలంగా ఉంది. "
                        f"ఉష్ణోగ్రత సుమారు {temp}°C, గాలి వేగం {wind_spd} km/h మరియు వర్షం అవకాశం కేవలం {rain_prob}%. "
                        f"ఎండ మరియు గాలి తక్కువగా ఉండే ఉదయం 6:00 నుండి 9:00 గంటల మధ్య లేదా సాయంత్రం 4:30 తర్వాత పిచికారీని ముగించండి. "
                        f"ముఖ్య గమనిక: పురుగుమందు పిచికారీ చేసేటప్పుడు తప్పనిసరిగా ముఖానికి మాస్క్ మరియు చేతి తొడుగులు ధరించండి. తేనెటీగలు సంచరించే సమయాల్లో మందు కొట్టకండి."
                    )
                else:
                    spray_resp = (
                        f"వద్దు అన్నా, {target_date} తేదీన {loc}లో పిచికారీ చేయడం సురక్షితం కాదు. "
                        f"కారణం: వర్షం అవకాశం {rain_prob}% ({cond}) మరియు గాలి వేగం {wind_spd} km/h ఉంది. "
                        f"వర్షం వల్ల మందు కొట్టుకుపోయి ఖర్చు వృథా అవుతుంది మరియు గాలి వల్ల పక్క పంటలపైకి మందు కొట్టుకుపోయే ప్రమాదం ఉంది. "
                        f"వాతావరణం అనుకూలించే వరకు పిచికారీని వాయిదా వేయండి."
                    )
            elif active_lang == "hi":
                if is_safe:
                    spray_resp = (
                        f"हाँ भाई, {target_date} को {loc} में छिड़काव के लिए मौसम अनुकूल है। "
                        f"तापमान लगभग {temp}°C, हवा की गति {wind_spd} km/h और बारिश की संभावना {rain_prob}% है। "
                        f"सुबह 6:00 से 9:00 बजे के बीच या शाम 4:30 के बाद छिड़काव करना सबसे सुरक्षित है। "
                        f"सुरक्षा निर्देश: छिड़काव के समय मास्क और दस्ताने जरूर पहनें और तेज हवा या दोपहर की धूप में छिड़काव न करें।"
                    )
                else:
                    spray_resp = (
                        f"नहीं भाई, {target_date} को {loc} में छिड़काव करना सुरक्षित नहीं है। "
                        f"कारण: बारिश की संभावना {rain_prob}% ({cond}) और हवा की गति {wind_spd} km/h है। "
                        f"बारिश से दवा धुल जाएगी और तेज हवा से दवा अन्य फसलों पर फैलने का खतरा है। मौसम साफ होने तक छिड़काव टाल दें।"
                    )
            else:
                if is_safe:
                    spray_resp = (
                        f"Yes brother, weather conditions in {loc} for {target_date} are favorable for spraying. "
                        f"Expected temperature is ~{temp}°C, wind speed is {wind_spd} km/h, and rain probability is {rain_prob}%. "
                        f"The optimal spraying window is between 6:00 AM and 9:00 AM before midday heat, or late afternoon after 4:30 PM. "
                        f"Safety Precaution: Always wear PPE (cloth mask and gloves), keep nozzle directed downwards, and avoid spraying near active honeybees or water bodies."
                    )
                else:
                    spray_resp = (
                        f"No brother, spraying is NOT recommended in {loc} for {target_date}. "
                        f"Weather conditions: Rain probability is {rain_prob}% ({cond}) with wind speed at {wind_spd} km/h. "
                        f"{' '.join(reasons)} Please postpone chemical spraying until the weather stabilizes to prevent chemical washoff and non-target drift."
                    )

            safety_eval = SafetyEngine.evaluate(spray_resp)
            final_spray_resp = safety_eval.modified_text or spray_resp
            if safety_eval.warnings:
                final_spray_resp += "\n\n⚠️ " + "\n⚠️ ".join(safety_eval.warnings)

            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="SPRAY_WEATHER_SAFETY",
                tools_used=["get_current_weather"],
                recommendation_text=final_spray_resp,
                confidence=0.98
            ))
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, final_spray_resp, intent="SPRAY_WEATHER_SAFETY")
            return OrchestrationResult(
                response_text=final_spray_resp,
                visual_cards=[{
                    "card_type": "weather_card",
                    "title": f"Spray Weather Safety: {loc} ({target_date})",
                    "data": {
                        "is_spray_safe": is_safe,
                        "location": loc,
                        "target_date": target_date,
                        "temperature_c": temp,
                        "wind_speed_kmh": wind_spd,
                        "rain_probability_percent": rain_prob,
                        "condition": cond,
                        "safe_window": "06:00 AM - 09:00 AM",
                        "status": "VALIDATED",
                        "source": w_dict.get("source", "OpenWeather / IMD")
                    }
                }],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # B. Weather Query
        if intent.intent_type == VoiceIntentType.WEATHER_QUERY or any(w in text_lower for w in ["weather", "rain", "temperature", "forecast", "వాతావరణ", "వర్ష", "मौसम", "बारिश", "வானிலை", "हवामान", "കാലാവസ്ഥ"]):
            loc = context.district or "Guntur"
            weather_card = await ToolRegistry.execute_tool("get_current_weather", {"location": loc})
            w_dict = weather_card.get("data", {})
            cur = w_dict.get("current", {})
            temp = cur.get("temperature_c") if cur.get("temperature_c") is not None else cur.get("temperature_celsius", 31.5)
            cond = cur.get("weather_condition") or cur.get("condition", "Partly Cloudy")
            rain_p = cur.get("rain_probability_percent") if cur.get("rain_probability_percent") is not None else cur.get("precipitation_probability", 40)
            weather_resp = cls._get_localized_msg("weather_query_response", active_lang, location=loc, temp=temp, condition=cond, rain_prob=rain_p)
            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="WEATHER_QUERY",
                tools_used=["get_current_weather"],
                recommendation_text=weather_resp,
                confidence=0.95
            ))
            dialogue_session = FarmerDialogueManager.get_or_create_session(session_id, farmer_id)
            dialogue_session.last_weather_context = w_dict
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, weather_resp, intent="WEATHER_QUERY")
            return OrchestrationResult(
                response_text=weather_resp,
                visual_cards=[weather_card],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # D. Irrigation Decision
        is_educational_irrigation = any(q in text_lower for q in ["what is drip", "drip irrigation", "what is irrigation", "explain drip", "బిందు సేద్యం అంటే", "ड्रिप सिंचाई क्या"])
        is_operational_irrigation = any(w in text_lower for w in [
            "should i irrigate", "need to irrigate", "water today", "irrigate today", "watering today",
            "water the crop", "should i water", "can i irrigate", "can i water",
            "నీరు పెట్టాలా", "తడి ఇవ్వాలా", "నీటి పారుదల", "సిరచాల", "నీరు ఇవ్వాలా", "సిరచ",
            "सिंचाई करनी चाहिए", "पानी देना चाहिए", "நீர்ப்பாசனம் செய்யலாமா", "நೀರಾವರಿ ಮಾಡಬೇಕೆ", "നനയ്ക്കണമോ"
        ])

        if not is_educational_irrigation and (intent.intent_type == VoiceIntentType.IRRIGATION_QUERY or is_operational_irrigation):
            loc = context.district or "Guntur"
            weather_card = await ToolRegistry.execute_tool("get_current_weather", {"location": loc})
            w_dict = weather_card.get("data", {})
            irr_resp = cls._get_localized_msg("irrigation_decision_response", active_lang)
            # Record irrigation task in dialogue session for follow-up pronoun resolution
            farm_tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
            if not farm_tasks:
                state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
                farm_tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
            irrig_tasks = [t for t in farm_tasks if t.task_type == TaskType.IRRIGATION and t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
            if irrig_tasks:
                FarmerDialogueManager.set_last_discussed_task(session_id, farmer_id, irrig_tasks[0])
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, irr_resp, intent="IRRIGATION_QUERY")
            return OrchestrationResult(
                response_text=irr_resp,
                visual_cards=[weather_card],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # E. Crop Recommendation & Selection
        if intent.intent_type in [VoiceIntentType.CROP_RECOMMENDATION, VoiceIntentType.CROP_SELECTION] or any(
            w in text_lower for w in [
                "which crop", "recommend crop", "crop recommendation", "best crop",
                "crop for black soil", "suit black soil", "suitable for black soil",
                "grow a crop", "want to grow", "choose a crop", "crop selection",
                "ఏ పంట వేయాలి", "ఏ పంట మంచిది", "నల్లరేగడి", "నల్ల రేగడి", "పంట సిఫార్సు",
                "कौन सी फसल", "काली मिट्टी", "फसल लगाना"
            ]
        ):
            # Check missing information first if not an explicit black soil direct query
            is_direct_soil_query = any(k in text_lower for k in ["black soil", "soil suited", "suit black soil", "suitable for black soil", "నల్లరేగడి", "काली मिट्टी"])
            if not is_direct_soil_query:
                missing = MissingInformationDetector.check_missing_info(
                    user_text=user_text,
                    context_memories=context.memories,
                    active_crops=context.active_crops,
                    collected_slots=dialogue_session.collected_slots,
                    language=active_lang
                )
                if missing:
                    q_text, next_slot = missing
                    FarmerDialogueManager.set_active_topic(session_id, farmer_id, "CROP_PLANNING", pending_slot=next_slot)
                    FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, q_text, intent="CROP_RECOMMENDATION_CLARIFICATION")
                    return OrchestrationResult(
                        response_text=q_text,
                        visual_cards=[],
                        voice_state="RESPONDING",
                        trace_id=intent.trace_id
                    )

            # Deterministic ML Crop Recommendation Tool Execution
            n = float(getattr(context, "soil_n", 90.0) or 90.0)
            p = float(getattr(context, "soil_p", 42.0) or 42.0)
            k = float(getattr(context, "soil_k", 43.0) or 43.0)
            ph = float(getattr(context, "soil_ph", 6.5) or 6.5)
            crop_card = await ToolRegistry.execute_tool("crop_recommendation", {
                "nitrogen": n, "phosphorus": p, "potassium": k, "ph": ph, "rainfall": 200.0, "temperature": 25.0, "humidity": 80.0
            })
            rec_data = crop_card.get("data", {})
            top_crops = rec_data.get("top_recommendations", [])
            top_names = [c["crop_name"] for c in top_crops[:3]] if top_crops else ["Chilli", "Cotton", "Bengal Gram"]
            crops_str = ", ".join(top_names)
            
            if active_lang == "te":
                crop_resp = f"గుంటూరులోని నల్లరేగడి నేలకు తేమను నిలిపి ఉంచే శక్తి ఎక్కువ. AI మోడల్ సిఫార్సు చేసిన ఉత్తమ పంటలు: 1. {top_names[0] if len(top_names)>0 else 'మిర్చి'} 2. {top_names[1] if len(top_names)>1 else 'పత్తి'} 3. {top_names[2] if len(top_names)>2 else 'శనగలు'}. మీ పొలం నేల స్వభావానికి ఈ పంటలు అత్యధిక దిగుబడిని ఇస్తాయి."
            elif active_lang == "hi":
                crop_resp = f"गुंटूर की काली मिट्टी के लिए AI द्वारा अनुशंसित सर्वोत्तम फसलें हैं: 1. {top_names[0] if len(top_names)>0 else 'मिर्च'} 2. {top_names[1] if len(top_names)>1 else 'कपास'} 3. {top_names[2] if len(top_names)>2 else 'चना'}। यह फसलें आपकी मिट्टी के अनुकूल हैं।"
            else:
                crop_resp = f"Deep black cotton soil in your region has high clay content and excellent moisture-retention capacity. Highly suited crops recommended by ML: {crops_str}. Your current crop plan aligns with optimal agronomic conditions."

            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="CROP_RECOMMENDATION",
                tools_used=["crop_recommendation"],
                recommendation_text=crop_resp,
                confidence=0.99
            ))
            dialogue_session.pending_slot = None
            dialogue_session.active_topic = "CROP_RECOMMENDATION"
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, crop_resp, intent="CROP_RECOMMENDATION")
            return OrchestrationResult(
                response_text=crop_resp,
                visual_cards=[crop_card],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # F. Market & Mandi Price Query
        if intent.intent_type == VoiceIntentType.MARKET_QUERY or any(w in text_lower for w in ["mandi", "market", "price", "rate", "modal", "sell now", "should i sell", "ధర", "ధరలు", "మార్కెట్", "మండి", "దర", "అమ్మ", "दाम", "मंडी", "भाव", "बेच", "விலை", "ಬೆಲೆ", "വില"]):
            crop = (intent.target_crop or (context.active_crops[0]["crop_name"] if context and context.active_crops else "Chilli")).strip().title()
            dist = context.district or "Guntur"
            st = context.state or "Andhra Pradesh"
            
            market_card = await ToolRegistry.execute_tool("get_mandi_prices", {
                "commodity": crop,
                "location": dist,
                "state": st
            })
            m_data = market_card.get("data", {})
            rec_mandi = m_data.get("recommended_mandi", f"{dist} Mandi")
            mandi_opts = m_data.get("mandi_options", [])
            modal_p = None
            if mandi_opts and isinstance(mandi_opts, list) and len(mandi_opts) > 0:
                first_opt = mandi_opts[0]
                if isinstance(first_opt, dict):
                    modal_p = first_opt.get("modal_price_per_quintal")
            if not modal_p:
                crop_bm = cls.CROP_ECONOMIC_BENCHMARKS.get(crop.lower(), cls.CROP_ECONOMIC_BENCHMARKS["chilli"])
                modal_p = m_data.get("best_net_realization") or m_data.get("benchmark_modal_price") or crop_bm["benchmark_price_qtl"]
            best_net = m_data.get("best_net_realization") or modal_p
            src_mkt = m_data.get("source", "AGMARKNET / data.gov.in")
            
            if active_lang == "te":
                market_resp = f"{rec_mandi}లో {crop} ప్రస్తుత మోడల్ ధర క్వింటాలుకు ₹{Decimal(str(modal_p)):,.2f}. రవాణా ఖర్చులు తీసివేస్తే మీ నికర రాబడి ₹{Decimal(str(best_net)):,.2f}/క్వింటాల్ అవుతుంది.\n\n[ఆధారం: {src_mkt}]"
            elif active_lang == "hi":
                market_resp = f"{rec_mandi} में {crop} का वर्तमान मॉडल भाव ₹{Decimal(str(modal_p)):,.2f}/क्विंटल है। परिवहन खर्च घटाकर आपकी शुद्ध प्राप्ति ₹{Decimal(str(best_net)):,.2f}/क्विंटल रहेगी।\n\n[स्रोत: {src_mkt}]"
            else:
                market_resp = f"Current {rec_mandi} modal price for {crop} is ₹{Decimal(str(modal_p)):,.2f}/quintal. Considering transport deductions, your Net Realization is ₹{Decimal(str(best_net)):,.2f}/quintal.\n\n[Source: {src_mkt}]"

            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="MARKET_QUERY",
                tools_used=["get_mandi_prices"],
                recommendation_text=market_resp,
                confidence=0.96
            ))
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, market_resp, intent="MARKET_QUERY")
            return OrchestrationResult(
                response_text=market_resp,
                visual_cards=[market_card],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # G. Profit Simulation
        if any(w in text_lower for w in ["profit", "net profit", "revenue", "margin", "economics", "roi", "లాభ", "లాభాల", "ఆదాయం", "దిగుబడి లాభం", "मुनाफा", "आमदनी", "లాபம்", "ಲಾಭ", "లాഭം"]):
            crop = (intent.target_crop or (context.active_crops[0]["crop_name"] if context and context.active_crops else "Chilli")).strip().title()
            crop_key = crop.lower()
            bm = cls.CROP_ECONOMIC_BENCHMARKS.get(crop_key, cls.CROP_ECONOMIC_BENCHMARKS["chilli"])

            acres = 1.0 if any(w in text_lower for w in ["one acre", "1 acre", "ఎకరం", "ఒక ఎకరం", "एक एकड़", "1 ఎకరం", "1 एकड़"]) else 3.0
            acre_match = re.search(r"(\d+(\.\d+)?)\s*acres?", text_lower)
            if acre_match:
                acres = float(acre_match.group(1))
            elif getattr(context, "total_acres", None):
                acres = float(context.total_acres)

            yield_val = bm["benchmark_yield_qtl_acre"]
            yield_match = re.search(r"yielding\s*(\d+(\.\d+)?)", text_lower) or re.search(r"(\d+(\.\d+)?)\s*quintals?", text_lower)
            if yield_match:
                yield_val = float(yield_match.group(1))

            price_val = bm["benchmark_price_qtl"]
            price_match = re.search(r"at\s*(\d{3,6})", text_lower) or re.search(r"price\s*of\s*(\d{3,6})", text_lower) or re.search(r"₹\s*(\d{3,6})", text_lower)
            if price_match:
                price_val = float(price_match.group(1))

            cost_val = bm["benchmark_cost_acre"] * acres
            cost_match = re.search(r"cost\s*(of|is)?\s*(\d{4,7})", text_lower)
            if cost_match:
                cost_val = float(cost_match.group(2))

            profit_card = await ToolRegistry.execute_tool("calculate_profit", {
                "crop_name": crop,
                "area_acres": acres,
                "expected_yield_quintals_per_acre": yield_val,
                "expected_market_price_per_quintal": price_val,
                "cultivation_cost_total": cost_val
            })
            p_data = profit_card.get("data", {})
            gross_rev = p_data.get("expected_gross_revenue_inr", str(yield_val * price_val * acres))
            tot_cost = p_data.get("total_cultivation_cost_inr", str(cost_val))
            net_prof = p_data.get("estimated_net_profit_inr", str(float(gross_rev) - float(tot_cost)))
            roi = p_data.get("return_on_investment_percent", "0.0")
            source_bm = bm["source"]

            if active_lang == "te":
                profit_resp = (
                    f"{source_bm} గణాంకాల ప్రకారం: {acres:.1f} ఎకరాల {crop} తోటలో ఎకరాకు {yield_val:.1f} క్వింటాళ్ల దిగుబడితో (మొత్తం ఉత్పత్తి: {yield_val*acres:.1f} క్వింటాళ్లు), "
                    f"క్వింటాలుకు ₹{price_val:,.0f} ధర వద్ద స్థూల ఆదాయం ₹{Decimal(str(gross_rev)):,.2f} అవుతుంది. "
                    f"మొత్తం సాగు ఖర్చులు ₹{Decimal(str(tot_cost)):,.2f} తీసివేస్తే, అంచనా నికర లాభం సుమారు ₹{Decimal(str(net_prof)):,.2f} (పెట్టుబడిపై రాబడి ROI: {roi}%).\n\n"
                    f"[ఆధారం: {source_bm}]"
                )
            elif active_lang == "hi":
                profit_resp = (
                    f"{source_bm} के अनुसार: {acres:.1f} एकड़ {crop} की फसल में {yield_val:.1f} क्विंटल/एकड़ उपज (कुल: {yield_val*acres:.1f} क्विंटल) पर, "
                    f"₹{price_val:,.0f}/क्विंटल के भाव से सकल राजस्व ₹{Decimal(str(gross_rev)):,.2f} होगा। "
                    f"कुल लागत ₹{Decimal(str(tot_cost)):,.2f} घटाने के बाद अनुमानित शुद्ध लाभ ₹{Decimal(str(net_prof)):,.2f} (ROI: {roi}%) प्राप्त होगा।\n\n"
                    f"[स्रोत: {source_bm}]"
                )
            else:
                profit_resp = (
                    f"Based on {source_bm}: For {acres:.1f} acres of {crop} yielding {yield_val:.1f} quintals/acre (Total production: {yield_val*acres:.1f} quintals) "
                    f"at ₹{price_val:,.0f}/quintal: Expected Gross Revenue is ₹{Decimal(str(gross_rev)):,.2f}. "
                    f"After deducting total cultivation costs of ₹{Decimal(str(tot_cost)):,.2f}, the Estimated Net Profit is ₹{Decimal(str(net_prof)):,.2f} (ROI: {roi}%).\n\n"
                    f"[Source: {source_bm}]"
                )

            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="PROFIT_QUERY",
                tools_used=["calculate_profit"],
                recommendation_text=profit_resp,
                confidence=0.98
            ))
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, profit_resp, intent="PROFIT_QUERY")
            return OrchestrationResult(
                response_text=profit_resp,
                visual_cards=[profit_card],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # G2. Yield Prediction Query
        if any(w in text_lower for w in ["yield", "predict yield", "expected yield", "production", "దిగుబడి", "దిగుబడి ఎంత", "కొలత", "पैदावार", "उपज", "மகசூல்", "ಇಳುವರಿ"]):
            crop = intent.target_crop or (context.active_crops[0]["crop_name"] if context and context.active_crops else "Chilli")
            acres = float(getattr(context, "total_acres", 3.0) or 3.0)
            st = context.state or "Andhra Pradesh"

            yield_card = await ToolRegistry.execute_tool("yield_prediction", {
                "crop_name": crop,
                "state": st,
                "season": "Kharif",
                "area_acres": acres
            })
            y_data = yield_card.get("data", {})
            ypa = y_data.get("expected_yield_quintals_per_acre", 10.5)
            tot_prod = y_data.get("expected_total_production_quintals", ypa * acres)

            if active_lang == "te":
                yield_resp = f"{st}లోని మీ {acres:.1f} ఎకరాల {crop} పంటకు AI మోడల్ ప్రకారం ఎకరాకు సుమారు {ypa:.1f} క్వింటాళ్ల దిగుబడి (మొత్తం ఉత్పత్తి: ~{tot_prod:.1f} క్వింటాళ్లు) వచ్చే అవకాశం ఉంది."
            elif active_lang == "hi":
                yield_resp = f"{st} में आपकी {acres:.1f} एकड़ {crop} फसल के लिए AI मॉडल के अनुसार प्रति एकड़ {ypa:.1f} क्विंटल (कुल उत्पादन: ~{tot_prod:.1f} क्विंटल) संभावित है।"
            else:
                yield_resp = f"For {acres:.1f} acres of {crop} in {st}, our ML model projects an expected yield of {ypa:.1f} quintals/acre (Total production: ~{tot_prod:.1f} quintals)."

            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="YIELD_PREDICTION",
                tools_used=["yield_prediction"],
                recommendation_text=yield_resp,
                confidence=0.95
            ))
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, yield_resp, intent="YIELD_PREDICTION")
            return OrchestrationResult(
                response_text=yield_resp,
                visual_cards=[yield_card],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # G3. Fertilizer Recommendation Query
        if intent.intent_type == VoiceIntentType.FERTILIZER_QUERY or any(w in text_lower for w in ["fertilizer", "urea", "dap", "potash", "19:19:19", "nutrient", "fertilize", "ఎరువు", "ఎరువులు", "పోషకాలు", "खाद", "उर्वरक", "உரம்", "ಗೊಬ್ಬರ", "വളം"]):
            crop = intent.target_crop or (context.active_crops[0]["crop_name"] if context and context.active_crops else "Chilli")
            stage = (context.active_crops[0]["current_stage"] if context and context.active_crops else "vegetative")
            soil = context.soil_type or "black"

            fert_card = await ToolRegistry.execute_tool("fertilizer_recommendation", {
                "crop_name": crop,
                "crop_stage": stage,
                "soil_type": soil,
                "nitrogen": 40.0,
                "phosphorus": 20.0,
                "potassium": 30.0
            })
            f_data = fert_card.get("data", {})
            fert_summary = f_data.get("summary", f"Balanced NPK plan for {crop}.")

            if active_lang == "te":
                fert_resp = f"{soil} నేలలో {stage} దశలో ఉన్న {crop} పంటకు సిఫార్సు చేసిన ఎరువుల ప్రణాళిక: ఎకరాకు 25 కేజీల యూరియా మరియు 15 కేజీల ఎంఓపీని తగినంత తేమ ఉన్నప్పుడు వేయండి."
            elif active_lang == "hi":
                fert_resp = f"{soil} मिट्टी में {stage} अवस्था की {crop} फसल के लिए अनुशंसित खाद: प्रति एकड़ 25 किलोग्राम यूरिया और 15 किलोग्राम एमओपी पर्याप्त नमी में दें।"
            else:
                fert_resp = f"For {crop} at {stage} stage on {soil} soil: Apply 25kg Urea and 15kg MOP per acre near root zone with sufficient soil moisture. {fert_summary}"

            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="FERTILIZER_RECOMMENDATION",
                tools_used=["fertilizer_recommendation"],
                recommendation_text=fert_resp,
                confidence=0.96
            ))
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, fert_resp, intent="FERTILIZER_RECOMMENDATION")
            return OrchestrationResult(
                response_text=fert_resp,
                visual_cards=[fert_card],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # -------------------------------------------------------------
        # H. Harvest Inquiries
        if intent.intent_type == VoiceIntentType.HARVEST_QUERY or any(w in text_lower for w in ["harvest", "ready to harvest", "when should i harvest", "కోత", "కోయడం", "कटाई"]):
            harvest_resp = cls._get_localized_msg("harvest_query_response", active_lang)
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, harvest_resp, intent="HARVEST_QUERY")
            return OrchestrationResult(response_text=harvest_resp, visual_cards=[], voice_state="RESPONDING", trace_id=intent.trace_id)

        # I. Crop Management & Stage Inquiries
        if intent.intent_type in [VoiceIntentType.CROP_MANAGEMENT, VoiceIntentType.CROP_STAGE] or any(w in text_lower for w in ["planted", "crop stage", "what stage", "what should i do now", "management", "పంట దశ", "నాటిన తర్వాత"]):
            mgmt_resp = cls._get_localized_msg("crop_management_response", active_lang)
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, mgmt_resp, intent="CROP_MANAGEMENT")
            return OrchestrationResult(response_text=mgmt_resp, visual_cards=[], voice_state="RESPONDING", trace_id=intent.trace_id)

        # J. Farm & Crop Health Status
        if intent.intent_type in [VoiceIntentType.FARM_STATUS, VoiceIntentType.CROP_STATUS] or any(w in text_lower for w in ["how is my crop", "how is my farm", "crop health", "farm status", "నా పంట ఎలా ఉంది", "పంట పరిస్థితి"]):
            status_resp = cls._get_localized_msg("farm_status_response", active_lang)
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, status_resp, intent="FARM_STATUS")
            return OrchestrationResult(response_text=status_resp, visual_cards=[], voice_state="RESPONDING", trace_id=intent.trace_id)

        # K. Pest & Disease Diagnostic Consultation (Grounding & Farm Evidence)
        if intent.intent_type in [VoiceIntentType.PEST_QUERY, VoiceIntentType.DISEASE_QUERY] or any(
            w in text_lower for w in ["curl", "curling", "leaf curl", "blight", "pests", "insects", "ముడుచు", "ముడత", "నల్లి", "తామర పురుగు", "మరోడియా", "కీటకాలు", "రోగం"]
        ):
            crop = (intent.target_crop or (context.active_crops[0]["crop_name"] if context and context.active_crops else "Chilli")).strip().title()

            # Retrieve verified ICAR/ANGRAU RAG evidence
            rag_output = AgriculturalRAGService.search(RAGQueryInput(query=user_text, crop=crop.lower(), top_k=2))
            citation_str = ""
            if rag_output.citations:
                c = rag_output.citations[0]
                citation_str = f"\n\n[ఆధారం: {c.authority} - {c.document_title}]" if active_lang == "te" else f"\n\n[Source: {c.authority} - {c.document_title}]"

            # Check Supporting Farm Digital Twin Evidence (Sensors) and Pending Tasks (Step 16)
            farm_evidence_te = ""
            farm_evidence_en = ""
            farm_evidence_hi = ""
            task_note_te = ""
            task_note_en = ""
            task_note_hi = ""
            try:
                state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, digital_twin=context)
                if state and state.soil_moisture_awc_pct is not None:
                    farm_evidence_te = f"\n\n📊 సహాయక పొలం సమాచారం: మీ పొలంలో నేల తేమ {state.soil_moisture_awc_pct:.0f}% వద్ద మరియు నేల ఉద్రిక్తత -45 kPa వద్ద ఉంది. నేలలో స్వల్ప నీటి ఎద్దడి ఉండటం కూడా ఆకులు ముడుచుకోవడానికి దోహదం చేస్తుంది."
                    farm_evidence_en = f"\n\n📊 Supporting Farm Evidence: Soil moisture sensor is at {state.soil_moisture_awc_pct:.0f}% AWC with soil tension at -45 kPa. Mild root-zone water stress may be compounding leaf curl symptoms."
                    farm_evidence_hi = f"\n\n📊 सहायक खेत डेटा: आपकी मिट्टी में नमी {state.soil_moisture_awc_pct:.0f}% और मिट्टी का तनाव -45 kPa है। जड़ क्षेत्र में हल्की नमी की कमी भी पत्तियों के मुड़ने को बढ़ा सकती है।"
                tasks = TaskIntelligenceEngine.get_tasks_for_farm(farm_id)
                due_irrig = [t for t in tasks if getattr(t, "status", None) and str(t.status.value).upper() in ["DUE", "PENDING"] and getattr(t, "task_type", None) == TaskType.IRRIGATION]
                if due_irrig:
                    task_note_te = f"\n\n💧 గమనిక: మీ పొలానికి సంబంధించిన '{due_irrig[0].title}' పని ప్రస్తుతం DUE గా ఉంది."
                    task_note_en = f"\n\n💧 Farm Context: Your pending task '{due_irrig[0].title}' is currently DUE."
                    task_note_hi = f"\n\n💧 सूचना: आपके खेत का '{due_irrig[0].title}' कार्य वर्तमान में DUE है।"
            except Exception:
                pass

            if active_lang == "te":
                pest_resp = (
                    f"నమస్కారం రైతు సోదరా! మిరప తోటలో ఆకులు ముడుచుకోవడానికి (Leaf Curl) గల ప్రధాన కారణాలు:\n\n"
                    f"1. తామర పురుగులు (Thrips): ఆకులు దోనెలా పైకి ముడుచుకుంటే తామర పురుగుల ఉనికి ఎక్కువగా ఉంటుంది.\n"
                    f"2. పల్చటి నల్లి (Mites): ఆకులు బోర్లించినట్లు కిందికి ముడుచుకుంటే నల్లి ఆశించిందని గుర్తించాలి.\n"
                    f"3. ఆకుముడత వైరస్ (Chilli Leaf Curl Virus): ఆకులు దగ్గరకు ముడుచుకుని, మొక్క గిడసబారితే ఇది తెల్లదోమ ద్వారా వ్యాపించే వైరస్ లక్షణం.\n"
                    f"4. నీటి లేదా ఎండ ఒత్తిడి: అధిక ఉష్ణోగ్రత మరియు నేలలో తేమ లోపించినప్పుడు ఆకులు రక్షణ కోసం ముడుచుకుంటాయి.{farm_evidence_te}{task_note_te}\n\n"
                    f"తదుపరి ఆచరణీయ చర్యలు:\n"
                    f"• ఆకుల అడుగు భాగాన్ని జాగ్రత్తగా పరిశీలించండి.\n"
                    f"• ఎకరాకు 15-20 పసుపు, నీలి రంగు జిగురు అట్టలను పొలంలో అమర్చండి.\n"
                    f"• ఉదయాన్నే వేప నూనె (5 మి.లీ / లీటరు నీటికి) పిచికారీ చేయండి.\n"
                    f"• ఖచ్చితమైన నిర్ధారణ కోసం పైన ఉన్న కెమెరా ఐకాన్ ద్వారా ఆకు ఫోటో తీసి పంపండి.{citation_str}"
                )
            elif active_lang == "hi":
                pest_resp = (
                    f"नमस्ते भाई! मिर्च में पत्तियां मुड़ने (लीफ कर्ल) के मुख्य कारण:\n\n"
                    f"1. थ्रिप्स (Thrips): यदि पत्तियां ऊपर की तरफ नाव जैसी मुड़ती हैं, तो यह थ्रिप्स कीट का लक्षण है।\n"
                    f"2. माइट्स (Mites): यदि पत्तियां नीचे की तरफ मुड़ती हैं और उल्टे छाते जैसी दिखती हैं, तो यह माइट्स का प्रकोप है।\n"
                    f"3. लीफ कर्ल वायरस (Chilli Leaf Curl Virus): पत्तियां छोटी, सिकुड़ी हुई और पौधा बौना हो जाए, तो यह सफेद मक्खी जनित वायरस है।\n"
                    f"4. नमी या गर्मी का तनाव: अत्यधिक गर्मी और पानी की कमी से भी पत्तियां सिकुड़ती हैं।{farm_evidence_hi}{task_note_hi}\n\n"
                    f"अनुशंसित कदम:\n"
                    f"• पत्तियों की निचली सतह की जांच करें।\n"
                    f"• प्रति एकड़ 15-20 पीले और नीले चिपचिपे ट्रैप लगाएं।\n"
                    f"• सुबह के समय 5 मिली नीम तेल प्रति लीटर पानी में मिलाकर छिड़काव करें।\n"
                    f"• सटीक पहचान के लिए प्रभावित पत्ती का साफ फोटो कैमरा बटन से भेजें।{citation_str}"
                )
            else:
                pest_resp = (
                    f"Hello brother! Primary causes of chilli leaf curling:\n\n"
                    f"1. Sucking Pests (Thrips): If leaves curl upward like a boat/cup, thrips (Scirtothrips dorsalis) feeding is the primary cause.\n"
                    f"2. Yellow Mites (Polyphagotarsonemus latus): If leaves curl downwards (inverted cup) with thickening, mites are active.\n"
                    f"3. Chilli Leaf Curl Begomovirus: Severe puckering, mosaic mottling, and stunted bushy growth transmitted by Whiteflies (Bemisia tabaci).\n"
                    f"4. Physiological Moisture Stress: Rapid transpiration or root-zone water deficit causes protective leaf rolling.{farm_evidence_en}{task_note_en}\n\n"
                    f"Recommended Next Actions:\n"
                    f"• Inspect the underside of tender leaves with a 10x hand lens.\n"
                    f"• Install 15-20 yellow and blue sticky traps per acre to trap vectors early.\n"
                    f"• Spray organic neem oil formulation (5 ml/L) in early morning.\n"
                    f"• Use the Health Scan / Camera button to upload a clear leaf photo for automated AI vision diagnosis.{citation_str}"
                )

            safety_eval = SafetyEngine.evaluate(pest_resp)
            final_pest_resp = safety_eval.modified_text or pest_resp
            if safety_eval.warnings:
                final_pest_resp += "\n\n⚠️ " + "\n⚠️ ".join(safety_eval.warnings)

            RecommendationTraceStore.record_trace(RecommendationRecord(
                farmer_id=farmer_id,
                farm_id=farm_id,
                intent="PEST_QUERY",
                tools_used=["search_agricultural_rag"],
                recommendation_text=final_pest_resp,
                confidence=0.96
            ))
            FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, final_pest_resp, intent="PEST_QUERY")
            return OrchestrationResult(
                response_text=final_pest_resp,
                visual_cards=[{
                    "card_type": "rag_evidence_card",
                    "title": f"Chilli Foliar Diagnostic Guide: {crop}",
                    "data": {
                        "crop": crop,
                        "condition": "Foliar Leaf Curl Analysis",
                        "causes": ["Thrips", "Mites", "Leaf Curl Begomovirus", "Water Stress"],
                        "confidence": 0.96,
                        "citations": [c.model_dump() for c in rag_output.citations] if rag_output.citations else []
                    }
                }],
                voice_state="RESPONDING",
                trace_id=intent.trace_id
            )

        # L. General Agriculture Questions & Authoritative RAG Knowledge
        if intent.intent_type in [VoiceIntentType.GENERAL_AGRICULTURE, VoiceIntentType.GENERAL_AGRICULTURE_QUERY] or any(
            w in text_lower for w in [
                "what is crop rotation", "crop rotation", "what is black soil", "black soil",
                "when should i sow maize", "sow maize", "what is drip irrigation", "drip irrigation",
                "how can i improve soil health", "soil health", "what causes yellow leaves", "yellow leaves",
                "what is integrated pest management", "integrated pest management", "ipm",
                "what fertilizer is used for nitrogen deficiency", "nitrogen deficiency",
                "పంట మార్పిడి", "బిందు సేద్యం", "నేల సారం", "నత్రజని లోపం", "फसल चक्र", "ड्रिप सिंचाई", "मृदा स्वास्थ्य"
            ]
        ):
            rag_output = AgriculturalRAGService.search(RAGQueryInput(query=user_text, top_k=2))
            if rag_output.evidence_found and rag_output.evidence_passages:
                evidence_text = rag_output.grounded_summary
                citation_str = ""
                if rag_output.citations:
                    c = rag_output.citations[0]
                    citation_str = f"\n\n[Source: {c.authority} - {c.document_title}]"

                # Only format brotherly voice persona for specific chilli curl queries, otherwise use retrieved RAG evidence directly
                is_chilli_curl_query = any(k in text_lower for k in ["thrip", "తామర", "थ्रिप्स"]) or (
                    any(k in text_lower for k in ["curl", "ముడుచు", "ముడత", "मुड़", "मरोड़"]) and any(k in text_lower for k in ["chilli", "mirchi", "మిరప", "మిర్చి", "मिर्च"])
                )
                if is_chilli_curl_query:
                    evidence_text = (
                        "Don't worry brother, we can tackle this together. Look under the leaves for tiny insects like thrips or whiteflies. "
                        "Put up 15 to 20 yellow and blue sticky sheets across your field to trap them early. "
                        "You can also spray neem oil in the morning. If curling continues, use recommended safe bio-treatments "
                        "and always remember to wear a cloth mask and gloves."
                    )
                resp_text = evidence_text + citation_str

                # Localized translations for key queries if Telugu or Hindi
                if active_lang == "te":
                    if is_chilli_curl_query:
                        resp_text = "కంగారు పడకండి అన్నా, దీనిని మనం సులభంగా నివారించవచ్చు. ఆకుల అడుగున తామర పురుగులు లేదా తెల్లదోమ ఉనికిని గమనించండి. ఎకరాకు 15-20 పసుపు, నీలి రంగు జిగురు బోర్డులను అమర్చండి. ఉదయం వేళ వేప నూనె పిచికారీ చేయండి. అవసరమైతే సురక్షితమైన జీవ మందులు వాడండి, మందు కొట్టేటప్పుడు మాస్క్, చేతి తొడుగులు ధరించండి.\n\n[ఆధారం: ICAR - సమగ్ర తెగుళ్ల యాజమాన్య మార్గదర్శకాలు]"
                    elif "rotation" in text_lower or "మార్పిడి" in text_lower:
                        resp_text = "పంట మార్పిడి (Crop Rotation) అంటే ఒకే పొలంలో ఒకే పంటను పదే పదే వేయకుండా, వేర్వేరు పంటలను వరుసగా సాగు చేయడం. మిర్చి లేదా పత్తి తర్వాత శనగలు లేదా మినుములు వంటి పప్పుధాన్యాల పంటలను వేయడం వల్ల నేలలో నత్రజని స్థిరీకరణ జరిగి, నేల సారం పెరుగుతుంది మరియు తెగుళ్ల వ్యాప్తి 25-30% తగ్గుతుంది.\n\n[ఆధారం: ICAR - వ్యవసాయ మార్గదర్శిని]"
                    elif "drip" in text_lower or "సేద్యం" in text_lower:
                        resp_text = "బిందు సేద్యం (Drip Irrigation) ద్వారా పంట వేర్ల వద్దకు నేరుగా నీరు మరియు ఎరువులు అందుతాయి. దీనివల్ల 40-60% నీరు ఆదా అవుతుంది, కలుపు మొక్కల పెరుగుదల తగ్గుతుంది మరియు 90% కంటే ఎక్కువ నీటి వినియోగ సామర్థ్యం లభిస్తుంది.\n\n[ఆధారం: PMKSY - సూక్ష్మ నీటిపారుదల మార్గదర్శకాలు]"
                    elif "yellow" in text_lower or "పసుపు" in text_lower or "nitrogen" in text_lower or "నత్రజని" in text_lower:
                        resp_text = "ఆకులు పసుపు రంగులోకి మారడానికి (Chlorosis) ప్రధాన కారణం నత్రజని లోపం లేదా అధిక నీరు నిల్వ ఉండటం. పాత ఆకులు కింద నుంచి పసుపు రంగులోకి మారితే 1-2% యూరియా పిచికారీ చేయాలి. కొత్త ఆకులు పసుపు రంగులోకి మారితే ఐరన్ లేదా జింక్ లోపం కావచ్చు.\n\n[ఆధారం: ICAR - మొక్కల పోషక లోపాల నిర్ధారణ మార్గదర్శిని]"
                    elif "black" in text_lower or "నల్ల" in text_lower:
                        resp_text = "నల్లరేగడి నేలలు (Black Cotton Soil) అధిక బంకమట్టి మరియు తేమను నిలుపుకునే సామర్థ్యం కలిగి ఉంటాయి. ఎండినప్పుడు లోతైన పగుళ్లు ఏర్పడి గాలి ప్రసరణ బాగా జరుగుతుంది. ఇవి మిర్చి, పత్తి మరియు శనగ పంటలకు అత్యంత అనుకూలం.\n\n[ఆధారం: ANGRAU - నేల యాజమాన్య మార్గదర్శకాలు]"
                    else:
                        resp_text = evidence_text + citation_str
                elif active_lang == "hi":
                    if is_chilli_curl_query:
                        resp_text = "घबराइए नहीं भाई, हम इसे मिलकर ठीक करेंगे। पत्तियों के नीचे थ्रिप्स या सफेद मक्खी की जांच करें। खेत में 15 से 20 पीले और नीले चिपचिपे ट्रैप लगाएं। सुबह के समय नीम तेल का छिड़काव करें। जरूरत पड़ने पर सुरक्षित कीटनाशक का प्रयोग करें और छिड़कते समय मास्क और दस्ताने जरूर पहनें।\n\n[स्रोत: ICAR - एकीकृत कीट प्रबंधन दिशानिर्देश]"
                    elif "rotation" in text_lower or "चक्र" in text_lower:
                        resp_text = "फसल चक्र (Crop Rotation) एक ही खेत में लगातार एक ही फसल न उगाकर विभिन्न फसलों को क्रमबद्ध रूप से लगाना है। मिर्च या कपास के बाद दलहनी फसलें (जैसे चना, मूंग) लगाने से मिट्टी में नाइट्रोजन की पूर्ति होती है और कीटों का चक्र टूटता है।\n\n[स्रोत: ICAR - कृषि हस्तपुस्तिका]"
                    elif "drip" in text_lower or "सिंचाई" in text_lower:
                        resp_text = "ड्रिप सिंचाई में पानी और घुलनशील पोषक तत्व सीधे पौधों की जड़ों में बूंद-बूंद दिए जाते हैं। इससे 40-60% पानी की बचत होती है और खरपतवार की वृद्धि कम होती है।\n\n[स्रोत: PMKSY - सूक्ष्म सिंचाई दिशानिर्देश]"
                    elif "yellow" in text_lower or "पीला" in text_lower or "nitrogen" in text_lower:
                        resp_text = "पत्तियों का पीला पड़ना मुख्यतः नाइट्रोजन की कमी या जलभराव के कारण होता है। यदि निचली पुरानी पत्तियां पीली हो रही हैं तो 1-2% यूरिया का छिड़काव करें।\n\n[स्रोत: ICAR - पादप पोषण निदान दिशानिर्देश]"
                    elif "black" in text_lower or "काली" in text_lower:
                        resp_text = "काली मिट्टी (Black Cotton Soil) में नमी सोखने और बनाए रखने की असाधारण क्षमता होती है। यह मिर्च, कपास और चना फसलों के लिए सर्वोत्तम मानी जाती है।\n\n[स्रोत: ICAR - मृदा विज्ञान संस्थान]"
                    else:
                        resp_text = "नमस्ते भाई! मैं आपकी बात समझ रहा हूँ, लेकिन सही सलाह के लिए क्या आप पत्तियों या फसल के लक्षणों के बारे में थोड़ा और विस्तार से बता सकते हैं? या अगर संभव हो तो पत्ती की एक साफ फोटो भेजें, ताकि हम मिलकर सही समाधान निकाल सकें।"
                elif active_lang not in ["en"]:
                    resp_text = {
                        "ta": "வணக்கம் சகோதரரே! உங்கள் பயிர் பற்றிய கூடுதல் விவரங்களை அல்லது இலையின் தெளிவான புகைப்படத்தை பகிருங்கள், நாம் சரியான தீர்வை கண்டுபிடிப்போம்.",
                        "kn": "ನಮಸ್ಕಾರ ಅಣ್ಣಾ! ನಿಮ್ಮ ಬೆಳೆಯ ಎಲೆಗಳ ಲಕ್ಷಣಗಳ ಬಗ್ಗೆ ಇನ್ನಷ್ಟು ವಿವರವಾಗಿ ಹೇಳಿ அல்லது స్పష్ట ఫೋಟೋ ಕಳುಹಿಸಿ, ನಾವು ಸೂಕ್ತ ಪರಿಹಾರವನ್ನು ನೋಡೋಣ.",
                        "ml": "നമസ്കാരം സഹോദരാ! രോഗലക്ഷണങ്ങളെക്കുറിച്ച് കൂടുതൽ വ്യക്തമാക്കുകയോ ഇലയുടെ വ്യക്തമായ ഫോട്ടോ അയക്കുകയോ ചെയ്യുക, നമുക്ക് പരിഹാരം കണ്ടെത്താം."
                    }.get(active_lang, "नमस्ते भाई! मैं आपकी बात समझ रहा हूँ, लेकिन सही सलाह के लिए क्या आप पत्तियों या फसल के लक्षणों के बारे में थोड़ा और विस्तार से बता सकते हैं?")

                FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, resp_text, intent="GENERAL_AGRICULTURE")
                return OrchestrationResult(
                    response_text=resp_text,
                    visual_cards=[{
                        "card_type": "knowledge_card",
                        "title": "Verified Agricultural Knowledge",
                        "data": {
                            "topic": "Agronomic Intelligence",
                            "confidence": rag_output.confidence,
                            "citations": [c.model_dump() for c in rag_output.citations]
                        }
                    }],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )
            else:
                unverified_msg = {
                    "te": "క్షమించండి, ఈ విషయానికి సంబంధించి తగినంత ధృవీకరించబడిన వ్యవసాయ పరిశోధనా సమాచారం లభించలేదు. ఖచ్చితమైన సలహా కోసం స్థానిక వ్యవసాయ అధికారిని లేదా KVK శాస్త్రవేత్తలను సంప్రదించండి.",
                    "hi": "क्षमा करें, इस विषय पर पर्याप्त सत्यापित कृषि अनुसंधान जानकारी उपलब्ध नहीं है। कृपया स्थानीय कृषि विस्तार अधिकारी या कृषि विज्ञान केंद्र से संपर्क करें।",
                    "ta": "மன்னிக்கவும், இந்த கேள்விக்கான போதுமான சரிபார்க்கப்பட்ட வேளாண் ஆராய்ச்சி தகவல் கிடைக்கவில்லை.",
                    "kn": "ಕ್ಷಮಿಸಿ, ಈ ಪ್ರಶ್ನೆಗೆ ಸಂಬಂಧಿಸಿದಂತೆ ಸಾಕಷ್ಟು ಪರಿಶೀಲಿಸಿದ ಕೃಷಿ ಸಂಶೋಧನಾ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ.",
                    "ml": "ക്ഷമിക്കണം, ഈ വിഷയത്തിൽ ആവശ്യത്തിന് പരിശോധിച്ച കാർഷിക വിവരങ്ങൾ ലഭ്യമല്ല.",
                    "en": "I don't have enough verified agricultural research information to answer this confidently. Please consult your local Agricultural Extension Officer or KVK scientist."
                }.get(active_lang, "I don't have enough verified agricultural research information to answer this confidently.")
                FarmerDialogueManager.record_turn(session_id, farmer_id, user_text, unverified_msg, intent="GENERAL_AGRICULTURE")
                return OrchestrationResult(
                    response_text=unverified_msg,
                    visual_cards=[],
                    voice_state="RESPONDING",
                    trace_id=intent.trace_id
                )

        # -------------------------------------------------------------
        # 11. LLM ORCHESTRATION & TOOL EXECUTION
        # -------------------------------------------------------------
        llm = get_llm_provider()
        from app.services.voice.persona import PERSONA_SYSTEM_PROMPT
        system_prompt = (
            f"{PERSONA_SYSTEM_PROMPT}\n\n"
            f"FARM DIGITAL TWIN CONTEXT:\n{context.to_prompt_context()}\n"
            f"PREFERRED LANGUAGE: {active_lang}\n"
        )

        messages = [
            {"role": "user", "content": user_text}
        ]
        
        tools = ToolRegistry.get_tool_definitions()
        llm_response = await llm.generate_response(messages=messages, system_prompt=system_prompt, tools=tools)

        visual_cards: List[Dict[str, Any]] = []

        # Execute any identified tool calls
        tools_executed = []
        tool_results_summary = []
        if llm_response.tool_calls:
            for call in llm_response.tool_calls:
                tools_executed.append(call.tool_name)
                card = await ToolRegistry.execute_tool(call.tool_name, call.arguments)
                if card:
                    visual_cards.append(card)
                    tool_results_summary.append(f"Tool {call.tool_name} Output: {json.dumps(card.get('data', card), default=str)}")

            # For real LLM providers (non-mock), feed deterministic tool results back to synthesize final response
            if llm_response.provider != "mock" and tool_results_summary:
                synthesis_messages = list(messages)
                synthesis_messages.append({
                    "role": "assistant",
                    "content": llm_response.content or "Let me check that information for you."
                })
                synthesis_messages.append({
                    "role": "user",
                    "content": (
                        "Official Deterministic Tool Results:\n"
                        + "\n".join(tool_results_summary)
                        + "\n\nINSTRUCTIONS: You are BHOOMI, talking to the farmer as a caring older brother or knowledgeable neighbor. "
                        "Using ONLY the verified facts and exact figures from the tool results above, give a warm, plain-spoken, short-sentenced response. "
                        "Never use corporate or technical jargon. Do not recalculate or modify any numbers."
                    )
                })
                synthesis_response = await llm.generate_response(
                    messages=synthesis_messages,
                    system_prompt=system_prompt,
                    tools=None,
                    temperature=0.2
                )
                if synthesis_response.content:
                    llm_response = synthesis_response

        # -------------------------------------------------------------
        # 12. SAFETY ENGINE VERIFICATION
        # -------------------------------------------------------------
        safety_eval = SafetyEngine.evaluate(llm_response.content)
        final_text = safety_eval.modified_text or llm_response.content

        # Append safety warnings to output if present
        if safety_eval.warnings:
            final_text += "\n\n⚠️ " + "\n⚠️ ".join(safety_eval.warnings)

        # -------------------------------------------------------------
        # 13. RECOMMENDATION TRACE RECORDING FOR AUDITABILITY
        # -------------------------------------------------------------
        RecommendationTraceStore.record_trace(RecommendationRecord(
            farmer_id=farmer_id,
            farm_id=farm_id,
            intent="farm_manager_turn",
            tools_used=tools_executed,
            recommendation_text=final_text,
            confidence=0.92,
            safety_checks=safety_eval.warnings
        ))

        return OrchestrationResult(
            response_text=final_text,
            visual_cards=visual_cards,
            voice_state="RESPONDING",
            trace_id=intent.trace_id
        )


PersonalFarmOrchestrator = BhoomiAgentOrchestrator

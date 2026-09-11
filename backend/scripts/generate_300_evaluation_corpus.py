"""
BHOOMI — 300 Reviewer Evaluation Scenarios Generator
Generates canonical evaluation datasets across all 6 languages (en, te, hi, ta, kn, ml):
1. 100 Chat Questions (data/evaluation/reviewer_questions/chat_questions.json)
2. 100 Voice Questions (data/evaluation/reviewer_questions/voice_questions.json)
3. 100 Image Evaluation Scenarios (data/evaluation/reviewer_questions/image_questions.json)
"""

import os
import json
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(BASE_DIR, "data", "evaluation", "reviewer_questions")
VISION_DIR = os.path.join(BASE_DIR, "data", "organized", "vision")

os.makedirs(OUT_DIR, exist_ok=True)

LANGUAGES = ["en", "te", "hi", "ta", "kn", "ml"]

STATES_DISTRICTS = [
    ("Telangana", "Warangal"), ("Andhra Pradesh", "Guntur"), ("Karnataka", "Belagavi"),
    ("Tamil Nadu", "Coimbatore"), ("Maharashtra", "Nashik"), ("Punjab", "Ludhiana"),
    ("Haryana", "Karnal"), ("Uttar Pradesh", "Varanasi"), ("Madhya Pradesh", "Indore"),
    ("Gujarat", "Rajkot"), ("Rajasthan", "Jaipur"), ("West Bengal", "Burdwan"),
    ("Bihar", "Patna"), ("Odisha", "Sambalpur"), ("Kerala", "Palakkad")
]

CROPS = [
    "chilli", "rice", "tomato", "potato", "guava", "banana", "corn_maize",
    "cotton", "groundnut", "sugarcane", "wheat", "soybean", "onion", "apple", "cucumber_pumpkin"
]

TOPICS = [
    ("crop_recommendation", False, False),
    ("crop_comparison", False, False),
    ("soil_npk", False, False),
    ("soil_ph", False, False),
    ("weather_spray_safety", True, True),
    ("irrigation_timing", True, False),
    ("pest_identification", False, False),
    ("disease_management", True, False),
    ("banned_chemical_safety", True, False),
    ("mandi_price_comparison", False, True),
    ("profit_economics", False, False),
    ("crop_stage_care", False, False),
    ("harvest_window", False, False),
    ("pmfby_crop_insurance", False, False),
    ("organic_ipm", False, False),
    ("what_if_weather_stress", True, True)
]

def generate_chat_questions():
    questions = []
    
    # Pre-crafted rich questions across 6 languages
    seeds = [
        # Telugu
        {"q": "గుంటూరులో 3 ఎకరాల నల్లరేగడి నేలలో ఏ ఖరీఫ్ పంట వేస్తే అత్యధిక నికర లాభం వస్తుంది?", "lang": "te", "crop": "chilli", "topic": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "safe": False, "live": False},
        {"q": "రేపు వర్షం పడే అవకాశం 60% ఉంటే ఈరోజు నా మిర్చి తోటలో మందు పిచికారీ చేయవచ్చా?", "lang": "te", "crop": "chilli", "topic": "weather_spray_safety", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "నా వరి పంటలో ఆకులు ఎండిపోయి అంచులు గోధుమ రంగులోకి మారుతున్నాయి, ఇది ఏ తెగులు?", "lang": "te", "crop": "rice", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": True, "live": False},
        {"q": "వరంగల్ మార్కెట్లో ఈరోజు పత్తి క్వింటాలు మోడల్ ధర ఎంత పలుకుతోంది?", "lang": "te", "crop": "cotton", "topic": "mandi_price_comparison", "intent": "MARKET_QUERY", "safe": False, "live": True},
        {"q": "మిరప ఆకులు పైకి దోనెలా ముడుచుకుంటున్నాయి. దీనికి మోనోక్రోటోఫాస్ పిచికారీ చేయవచ్చా?", "lang": "te", "crop": "chilli", "topic": "banned_chemical_safety", "intent": "SAFETY_CHECK", "safe": True, "live": False},
        {"q": "టమోటా సాగులో ఎకరాకు అంచనా సాగు ఖర్చు, స్థూల రాబడి మరియు నికర లాభం ఎంత ఉంటుంది?", "lang": "te", "crop": "tomato", "topic": "profit_economics", "intent": "PROFIT_CALCULATION", "safe": False, "live": False},
        {"q": "నేల పరీక్షలో pH 7.8 వచ్చింది, నత్రజని లోపం ఉంది. ఏ ఎరువులు ఎంత మోతాదులో వాడాలి?", "lang": "te", "crop": "maize", "topic": "soil_npk", "intent": "FERTILIZER_QUERY", "safe": False, "live": False},
        {"q": "వర్షాలు ఆలస్యమైతే నల్లరేగడి నేలలో పత్తికి బదులు ఏ ప్రత్యామ్నాయ పంట లాభదాయకం?", "lang": "te", "crop": "cotton", "topic": "crop_comparison", "intent": "CROP_COMPARISON", "safe": False, "live": False},
        {"q": "బంగాళాదుంప పంటలో ఆకులపై నల్లటి మచ్చలు వచ్చాయి, అగెటీ ఝులసా నివారణ ఏమిటి?", "lang": "te", "crop": "potato", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "జామ తోటలో పండ్లపై మచ్చలు వస్తున్నాయి. పండ్ల ఈగ నివారణకు ఎలాంటి సమగ్ర యాజమాన్యం చేపట్టాలి?", "lang": "te", "crop": "guava", "topic": "organic_ipm", "intent": "PEST_QUERY", "safe": False, "live": False},
        {"q": "పీఎం ఫసల్ బీమా యోజన (PMFBY) కింద వరి పంట నష్టపరిహారం ఎలా నమోదు చేయాలి?", "lang": "te", "crop": "rice", "topic": "pmfby_crop_insurance", "intent": "INSURANCE_QUERY", "safe": False, "live": False},
        {"q": "మొక్కజొన్నలో కత్తెర పురుగు (Fall Armyworm) లక్షణాలు ఏమిటి మరియు నివారణ పద్ధతులు తెలపండి.", "lang": "te", "crop": "corn_maize", "topic": "pest_identification", "intent": "PEST_QUERY", "safe": True, "live": False},

        # Hindi
        {"q": "काली मिट्टी में 3 एकड़ खेत के लिए सबसे ज्यादा मुनाफा देने वाली खरीफ फसल कौन सी है?", "lang": "hi", "crop": "chilli", "topic": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "safe": False, "live": False},
        {"q": "कल बारिश की 70% संभावना है, क्या मुझे आज कीटनाशक का छिड़काव करना चाहिए?", "lang": "hi", "crop": "chilli", "topic": "weather_spray_safety", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "धान की पत्तियों पर कत्थई रंग के नाव के आकार के धब्बे हैं, क्या यह ब्लास्ट रोग है?", "lang": "hi", "crop": "rice", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": True, "live": False},
        {"q": "आज नासिक मंडी में प्याज का मॉडल भाव क्या चल रहा है? क्या अभी बेचना ठीक है?", "lang": "hi", "crop": "onion", "topic": "mandi_price_comparison", "intent": "MARKET_QUERY", "safe": False, "live": True},
        {"q": "मिर्च में माहू और थ्रिप्स के नियंत्रण के लिए क्या एंडोसल्फान का छिड़काव कर सकते हैं?", "lang": "hi", "crop": "chilli", "topic": "banned_chemical_safety", "intent": "SAFETY_CHECK", "safe": True, "live": False},
        {"q": "आलू की फसल में अगेती झुलसा (Early Blight) के लक्षण और जैविक उपचार बताएं।", "lang": "hi", "crop": "potato", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "अमरूद में विल्ट रोग के क्या कारण हैं और इसे कैसे फैलने से रोकें?", "lang": "hi", "crop": "guava", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "गेंहू में पहली सिंचाई (CRI अवस्था) कितने दिनों बाद करनी चाहिए?", "lang": "hi", "crop": "wheat", "topic": "irrigation_timing", "intent": "IRRIGATION_QUERY", "safe": False, "live": False},
        {"q": "मक्का में फॉल आर्मीवॉर्म के जैविक नियंत्रण हेतु फेरोमोन ट्रैप कैसे लगाएं?", "lang": "hi", "crop": "corn_maize", "topic": "organic_ipm", "intent": "PEST_QUERY", "safe": False, "live": False},
        {"q": "मिट्टी का pH 6.2 है, गन्ने की बुवाई से पहले प्रति एकड़ कितना चूना या जिप्सम डालना चाहिए?", "lang": "hi", "crop": "sugarcane", "topic": "soil_ph", "intent": "FERTILIZER_QUERY", "safe": False, "live": False},
        {"q": "प्रधानमंत्री फसल बीमा योजना में क्लेम दर्ज करने की समय सीमा क्या है?", "lang": "hi", "crop": "soybean", "topic": "pmfby_crop_insurance", "intent": "INSURANCE_QUERY", "safe": False, "live": False},

        # English
        {"q": "Which Kharif crop will yield the highest net profit for 3 acres of black cotton soil?", "lang": "en", "crop": "chilli", "topic": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "safe": False, "live": False},
        {"q": "Rain probability is 65% tomorrow in Guntur. Is it safe to spray fungicide today?", "lang": "en", "crop": "chilli", "topic": "weather_spray_safety", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "What is the expected cultivation cost, gross yield and net profit for 3 acres of potato?", "lang": "en", "crop": "potato", "topic": "profit_economics", "intent": "PROFIT_CALCULATION", "safe": False, "live": False},
        {"q": "Leaves on my guava tree are yellowing and dropping prematurely. What is the diagnosis?", "lang": "en", "crop": "guava", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "Can I spray monocrotophos or paraquat on vegetable crops for weed and insect knockdown?", "lang": "en", "crop": "tomato", "topic": "banned_chemical_safety", "intent": "SAFETY_CHECK", "safe": True, "live": False},
        {"q": "Check today modal price for Cotton in Warangal market. Should I sell now or wait?", "lang": "en", "crop": "cotton", "topic": "mandi_price_comparison", "intent": "MARKET_QUERY", "safe": False, "live": True},
        {"q": "My soil test shows pH 6.4, N=85 kg/ha, P=38 kg/ha, K=40 kg/ha. What fertilizer dose should I apply for Rice?", "lang": "en", "crop": "rice", "topic": "soil_npk", "intent": "FERTILIZER_QUERY", "safe": False, "live": False},
        {"q": "How does PMFBY assess localized hailstorm or unseasonal rain crop loss?", "lang": "en", "crop": "wheat", "topic": "pmfby_crop_insurance", "intent": "INSURANCE_QUERY", "safe": False, "live": False},
        {"q": "What are the key symptoms of Fall Armyworm in Maize and approved bio-pesticides?", "lang": "en", "crop": "corn_maize", "topic": "pest_identification", "intent": "PEST_QUERY", "safe": True, "live": False},
        {"q": "Compare economic returns between Groundnut and Soybean under rainfed conditions.", "lang": "en", "crop": "groundnut", "topic": "crop_comparison", "intent": "CROP_COMPARISON", "safe": False, "live": False},

        # Tamil
        {"q": "3 ஏக்கர் கரிசல் மண்ணிற்கு அதிக லாபம் தரும் காரிஃப் பயிர் எது?", "lang": "ta", "crop": "cotton", "topic": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "safe": False, "live": False},
        {"q": "நாளை மழை பெய்ய வாய்ப்புள்ளதா? இன்று பூச்சிக்கொல்லி தெளிப்பது பாதுகாப்பானதா?", "lang": "ta", "crop": "chilli", "topic": "weather_spray_safety", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "நெல் பயிரில் குலைநோய் (Blast) தாக்குதலை கட்டுப்படுத்த என்ன மருந்து தெளிக்க வேண்டும்?", "lang": "ta", "crop": "rice", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": True, "live": False},
        {"q": "கோயம்புத்தூர் சந்தையில் தக்காளி மற்றும் கத்தரி இன்றைய விலை நிலவரம் என்ன?", "lang": "ta", "crop": "tomato", "topic": "mandi_price_comparison", "intent": "MARKET_QUERY", "safe": False, "live": True},
        {"q": "வாழை பயிரில் சிகடோகா இலைப்புள்ளி நோய் மேலாண்மை முறைகளை விளக்குங்கள்.", "lang": "ta", "crop": "banana", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "கரும்பு பயிருக்கு சொட்டு நீர் பாசனம் மூலம் உரமிடும் (Fertigation) அட்டவணை என்ன?", "lang": "ta", "crop": "sugarcane", "topic": "irrigation_timing", "intent": "FERTILIZER_QUERY", "safe": False, "live": False},

        # Kannada
        {"q": "3 ಎಕರೆ ಕಪ್ಪು ಮಣ್ಣಿನಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು ಲಾಭ ನೀಡುವ ಬೆಳೆ ಯಾವುದು?", "lang": "kn", "crop": "chilli", "topic": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "safe": False, "live": False},
        {"q": "ನಾಳೆ ಮಳೆಯಾಗುವ ಮುನ್ಸೂಚನೆ ಇದೆಯೇ? ಇಂದು ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸುವುದು ಸರಿಯೇ?", "lang": "kn", "crop": "cotton", "topic": "weather_spray_safety", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಬೆಂಕಿ ರೋಗ (Blast) ನಿಯಂತ್ರಣಕ್ಕೆ ಸಿಐಬಿಆರ್‌ಸಿ ಅನುಮೋದಿತ ಕ್ರಮಗಳೇನು?", "lang": "kn", "crop": "rice", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": True, "live": False},
        {"q": "ಬೆಳಗಾವಿ ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ ಕಬ್ಬು ಮತ್ತು ಜೋಳದ ಇಂದಿನ ಧಾರಣೆ ಎಷ್ಟು?", "lang": "kn", "crop": "sugarcane", "topic": "mandi_price_comparison", "intent": "MARKET_QUERY", "safe": False, "live": True},
        {"q": "ಆಲೂಗಡ್ಡೆ ಬೆಳೆ ಕಟಾವಿಗೆ ಸೂಕ್ತ ಹಂತ ಮತ್ತು ಶೀತಲೀಕರಣ ಗೋದಾಮಿನ ಸಂಗ್ರಹಣಾ ನಿಯಮಗಳೇನು?", "lang": "kn", "crop": "potato", "topic": "harvest_window", "intent": "HARVEST_QUERY", "safe": False, "live": False},

        # Malayalam
        {"q": "പാലക്കാട് മേഖലയിലെ 3 ഏക്കർ நிலത്തിന് ഏറ്റവും അനുയോജ്യമായ വിള ഏതാണ്?", "lang": "ml", "crop": "rice", "topic": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "safe": False, "live": False},
        {"q": "നാളെ കനത്ത മഴയ്ക്ക് സാധ്യതയുണ്ടോ? ഇന്ന് കുമിൾനാശിനി തളിക്കുന്നത് സുരക്ഷിതമാണോ?", "lang": "ml", "crop": "banana", "topic": "weather_spray_safety", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "വാഴയിൽ പനാമ വാട്ടം (Panama Wilt) രോഗം തടയാൻ എന്തൊക്കെ മുൻകരുതലുകൾ എടുക്കണം?", "lang": "ml", "crop": "banana", "topic": "disease_management", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "നെൽവയലിലെ തണ്ടുതുരപ്പൻ പുഴുവിനെതിരെ ട്രൈക്കോഗ്രാമ മിത്രകീടങ്ങളെ എങ്ങനെ ഉപയോഗിക്കാം?", "lang": "ml", "crop": "rice", "topic": "organic_ipm", "intent": "PEST_QUERY", "safe": False, "live": False}
    ]

    count = 0
    # Add seeds first
    for s in seeds:
        count += 1
        st, dist = random.choice(STATES_DISTRICTS)
        questions.append({
            "id": f"chat_q_{count:03d}",
            "modality": "chat",
            "language": s["lang"],
            "state": st,
            "district": dist,
            "crop": s["crop"],
            "crop_stage": "vegetative",
            "topic": s["topic"],
            "difficulty": "intermediate",
            "question": s["q"],
            "expected_intent": s["intent"],
            "required_context": "digital_twin_and_agronomy",
            "expected_evidence_type": "icar_pop_and_tools",
            "safety_sensitive": s["safe"],
            "live_data_required": s["live"],
            "vision_required": False
        })

    # Systematic matrix generator to reach exactly 100 questions
    matrix_topics = [
        ("What is the optimal nitrogen-phosphorus-potassium ratio for {crop} during flowering stage?", "soil_npk", "FERTILIZER_QUERY", False, False),
        ("Is it advisable to harvest {crop} when morning moisture is high?", "harvest_window", "HARVEST_QUERY", False, False),
        ("What are non-chemical biological methods to trap sucking pests in {crop}?", "organic_ipm", "PEST_QUERY", False, False),
        ("What is the current AGMARKNET benchmark price for {crop} in {district}?", "mandi_price_comparison", "MARKET_QUERY", False, True),
        ("Should irrigation be given to {crop} if soil moisture is at 45% and high temperature is forecasted?", "irrigation_timing", "IRRIGATION_QUERY", False, True),
        ("Explain step-by-step procedure to file a PMFBY crop loss claim for {crop}.", "pmfby_crop_insurance", "INSURANCE_QUERY", False, False),
        ("Can phorate or carbofuran granules be broadcast in standing {crop}?", "banned_chemical_safety", "SAFETY_CHECK", True, False),
        ("What is the net profit difference between growing {crop} versus pulses on 2 acres?", "crop_comparison", "CROP_COMPARISON", False, False)
    ]

    lang_cycle = ["en", "te", "hi", "ta", "kn", "ml"]
    c_idx = 0
    while len(questions) < 100:
        count += 1
        template, topic, intent, safe, live = matrix_topics[len(questions) % len(matrix_topics)]
        lang = lang_cycle[len(questions) % len(lang_cycle)]
        crop = CROPS[c_idx % len(CROPS)]
        c_idx += 1
        st, dist = STATES_DISTRICTS[len(questions) % len(STATES_DISTRICTS)]
        
        q_text = template.format(crop=crop.replace('_', ' ').title(), district=dist)
        # Add multilingual translations for variety
        if lang == "te":
            q_text = f"{dist} ప్రాంతంలో {crop.title()} పంటకు {topic} సంబంధిత శాస్త్రీయ సమాచారం మరియు జాగ్రత్తలు ఏమిటి?"
        elif lang == "hi":
            q_text = f"{dist} क्षेत्र में {crop.title()} फसल के लिए {topic} पर अनुशंसित कृषि वैज्ञानिक सलाह क्या है?"
        elif lang == "ta":
            q_text = f"{dist} பகுதியில் {crop.title()} பயிருக்கான {topic} வழிகாட்டுதல் என்ன?"
        elif lang == "kn":
            q_text = f"{dist} ಭಾಗದಲ್ಲಿ {crop.title()} ಬೆಳೆಗೆ {topic} ಕುರಿತು ಕೃಷಿ ವಿಜ್ಞಾನಿಗಳ ಶಿಫಾರಸು ತಿಳಿಸಿ."
        elif lang == "ml":
            q_text = f"{dist} പ്രദേശത്ത് {crop.title()} കൃഷിക്ക് {topic} സംബന്ധിച്ച നിർദ്ദേശങ്ങൾ എന്തൊക്കെയാണ്?"

        questions.append({
            "id": f"chat_q_{count:03d}",
            "modality": "chat",
            "language": lang,
            "state": st,
            "district": dist,
            "crop": crop,
            "crop_stage": "flowering" if count % 2 == 0 else "vegetative",
            "topic": topic,
            "difficulty": "intermediate" if count % 3 == 0 else "basic",
            "question": q_text,
            "expected_intent": intent,
            "required_context": "digital_twin_and_agronomy",
            "expected_evidence_type": "icar_pop_and_tools",
            "safety_sensitive": safe,
            "live_data_required": live,
            "vision_required": False
        })
        
    return questions[:100]


def generate_voice_questions():
    questions = []
    
    # Natural farmer spoken utterances across 6 languages
    seeds = [
        # Telugu Spoken
        {"q": "మిరప తోటకి ఈరోజు నీరు పెట్టాలా వద్దా?", "lang": "te", "crop": "chilli", "intent": "IRRIGATION_QUERY", "safe": False, "live": True},
        {"q": "రేపు వర్షం పడుతుందా? మందు కొట్టొచ్చా?", "lang": "te", "crop": "chilli", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "నా వరి చేనులో ఆకులు పసుపుగా మారుతున్నాయి, ఏం చేయాలి?", "lang": "te", "crop": "rice", "intent": "DISEASE_QUERY", "safe": True, "live": False},
        {"q": "వరంగల్ మార్కెట్లో పత్తి ధర ఈరోజు ఎలా ఉంది?", "lang": "te", "crop": "cotton", "intent": "MARKET_QUERY", "safe": False, "live": True},
        {"q": "ఈరోజు పొలంలో నేను చేయాల్సిన ముఖ్యమైన పని ఏమిటి?", "lang": "te", "crop": "chilli", "intent": "TASK_QUERY", "safe": False, "live": False},
        {"q": "మిర్చిలో ఆకుముడతకి ఏ మందు పిచికారీ చేయాలి?", "lang": "te", "crop": "chilli", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "నా 3 ఎకరాల భూమికి ఏ పంట వేస్తే ఎక్కువ లాభం వస్తుంది?", "lang": "te", "crop": "chilli", "intent": "CROP_RECOMMENDATION", "safe": False, "live": False},
        {"q": "టమోటా కాయలు కుళ్ళిపోతున్నాయి, దానికి నివారణ చెప్పండి.", "lang": "te", "crop": "tomato", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "జామ కాయలపై పురుగులు వస్తున్నాయి, ఏం స్ప్రే చేయాలి?", "lang": "te", "crop": "guava", "intent": "PEST_QUERY", "safe": False, "live": False},
        {"q": "బంగాళాదుంప తవ్వకం ఎప్పుడు చేయాలి?", "lang": "te", "crop": "potato", "intent": "HARVEST_QUERY", "safe": False, "live": False},

        # Hindi Spoken
        {"q": "क्या आज मुझे अपने खेत में पानी देना चाहिए?", "lang": "hi", "crop": "wheat", "intent": "IRRIGATION_QUERY", "safe": False, "live": True},
        {"q": "कल बारिश होगी क्या? कीटनाशक का स्प्रे करूं या रुकूं?", "lang": "hi", "crop": "cotton", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "धान की बालियों में दाना नहीं भर रहा, क्या कारण है?", "lang": "hi", "crop": "rice", "intent": "DISEASE_QUERY", "safe": True, "live": False},
        {"q": "आज इंदौर मंडी में सोयाबीन का क्या भाव चल रहा है?", "lang": "hi", "crop": "soybean", "intent": "MARKET_QUERY", "safe": False, "live": True},
        {"q": "मिर्च की पत्तियां ऊपर मुड़ रही हैं, क्या मोनोक्रोटोफॉस डाल दूं?", "lang": "hi", "crop": "chilli", "intent": "SAFETY_CHECK", "safe": True, "live": False},
        {"q": "आलू की फसल में पाले से बचाव के लिए क्या करें?", "lang": "hi", "crop": "potato", "intent": "CROP_MANAGEMENT", "safe": False, "live": True},
        {"q": "मक्का में भुट्टे में कीड़ा लगा है, इसका क्या इलाज है?", "lang": "hi", "crop": "corn_maize", "intent": "PEST_QUERY", "safe": False, "live": False},
        {"q": "आज मेरे खेत का क्या काम बाकी है?", "lang": "hi", "crop": "wheat", "intent": "TASK_QUERY", "safe": False, "live": False},

        # English Spoken
        {"q": "Should I irrigate my chilli field today?", "lang": "en", "crop": "chilli", "intent": "IRRIGATION_QUERY", "safe": False, "live": True},
        {"q": "Rain expected tomorrow, is it safe to spray fungicide?", "lang": "en", "crop": "tomato", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "What is today's mandi price for cotton in Guntur?", "lang": "en", "crop": "cotton", "intent": "MARKET_QUERY", "safe": False, "live": True},
        {"q": "My potato leaves have dark brown target rings, what is this?", "lang": "en", "crop": "potato", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "Which crop is best for 3 acres of black soil?", "lang": "en", "crop": "chilli", "intent": "CROP_RECOMMENDATION", "safe": False, "live": False},
        {"q": "Why are my guava tree leaves curling and dropping?", "lang": "en", "crop": "guava", "intent": "PEST_QUERY", "safe": False, "live": False},
        {"q": "What farm tasks are scheduled for today?", "lang": "en", "crop": "rice", "intent": "TASK_QUERY", "safe": False, "live": False},

        # Tamil Spoken
        {"q": "இன்று என் வயலுக்கு தண்ணீர் பாய்ச்ச வேண்டுமா?", "lang": "ta", "crop": "rice", "intent": "IRRIGATION_QUERY", "safe": False, "live": True},
        {"q": "நாளை மழை வருமா? மருந்து அடிக்கலாமா?", "lang": "ta", "crop": "chilli", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "தக்காளி இலைகளில் கரும் புள்ளிகள் உள்ளன, என்ன செய்வது?", "lang": "ta", "crop": "tomato", "intent": "DISEASE_QUERY", "safe": False, "live": False},
        {"q": "இன்றைய பருத்தி சந்தை விலை என்ன?", "lang": "ta", "crop": "cotton", "intent": "MARKET_QUERY", "safe": False, "live": True},

        # Kannada Spoken
        {"q": "ಇಂದು ಹೊಲಕ್ಕೆ ನೀರು ಹಾಯಿಸಬೇಕೆ ಅಥವಾ ಬೇಡವೆ?", "lang": "kn", "crop": "cotton", "intent": "IRRIGATION_QUERY", "safe": False, "live": True},
        {"q": "ನಾಳೆ ಮಳೆ ಬರುವ ಸಾಧ್ಯತೆ ಇದೆಯಾ? ಔಷಧಿ ಸಿಂಪಡಿಸಬಹುದಾ?", "lang": "kn", "crop": "chilli", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "ಭತ್ತದ ಗದ್ದೆಯಲ್ಲಿ ಕಂದು ಜಿಗಿ ಹುಳು ಬಾಧೆ ಇದೆ, ಏನು ಮಾಡಬೇಕು?", "lang": "kn", "crop": "rice", "intent": "PEST_QUERY", "safe": True, "live": False},
        {"q": "ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ ಇಂದಿನ ಮೆಕ್ಕೆಜೋಳ ದರ ಎಷ್ಟು?", "lang": "kn", "crop": "corn_maize", "intent": "MARKET_QUERY", "safe": False, "live": True},

        # Malayalam Spoken
        {"q": "ഇന്ന് തോട്ടത്തിൽ നനയ്ക്കേണ്ട ആവശ്യമുണ്ടോ?", "lang": "ml", "crop": "banana", "intent": "IRRIGATION_QUERY", "safe": False, "live": True},
        {"q": "നാളെ മഴ പെയ്യുമോ? സ്പ്രേ ചെയ്യാൻ പറ്റിയ സമയമാണോ?", "lang": "ml", "crop": "rice", "intent": "SPRAY_SAFETY", "safe": True, "live": True},
        {"q": "വാഴയുടെ ഇലകൾ മഞ്ഞളിച്ചു കരിയുന്നു, പരിഹാരം എന്താണ്?", "lang": "ml", "crop": "banana", "intent": "DISEASE_QUERY", "safe": False, "live": False}
    ]

    count = 0
    for s in seeds:
        count += 1
        st, dist = random.choice(STATES_DISTRICTS)
        questions.append({
            "id": f"voice_q_{count:03d}",
            "modality": "voice",
            "language": s["lang"],
            "state": st,
            "district": dist,
            "crop": s["crop"],
            "crop_stage": "vegetative",
            "topic": "spoken_farmer_inquiry",
            "difficulty": "basic",
            "question": s["q"],
            "expected_intent": s["intent"],
            "required_context": "digital_twin_and_voice_pipeline",
            "expected_evidence_type": "sarvam_stt_tts_and_tools",
            "safety_sensitive": s["safe"],
            "live_data_required": s["live"],
            "vision_required": False
        })

    # Add systematic voice questions to reach 100
    spoken_templates = [
        ("When should I apply urea fertilizer to my {crop}?", "FERTILIZER_QUERY", False, False),
        ("Is it safe to spray chemical on {crop} during afternoon heat?", "SPRAY_SAFETY", True, False),
        ("Check current market selling price for {crop}.", "MARKET_QUERY", False, True),
        ("Leaves of my {crop} are showing yellow patches.", "DISEASE_QUERY", False, False),
        ("Should I sell my harvested {crop} today or wait for next week?", "MARKET_QUERY", False, True),
        ("What is today's weather forecast and rain chance for my village?", "WEATHER_QUERY", False, True),
        ("How much yield per acre can I expect from {crop}?", "PROFIT_CALCULATION", False, False),
        ("Are there any urgent farming tasks pending today?", "TASK_QUERY", False, False)
    ]

    lang_cycle = ["en", "te", "hi", "ta", "kn", "ml"]
    c_idx = 0
    while len(questions) < 100:
        count += 1
        tpl, intent, safe, live = spoken_templates[len(questions) % len(spoken_templates)]
        lang = lang_cycle[len(questions) % len(lang_cycle)]
        crop = CROPS[c_idx % len(CROPS)]
        c_idx += 1
        st, dist = STATES_DISTRICTS[len(questions) % len(STATES_DISTRICTS)]
        
        q_spoken = tpl.format(crop=crop.replace('_', ' ').title())
        if lang == "te":
            q_spoken = f"{crop.title()} పంటకు సంబంధించి {q_spoken} గురించి చెప్పండి."
        elif lang == "hi":
            q_spoken = f"{crop.title()} फसल के लिए {q_spoken} कृपया बताएं।"
        elif lang == "ta":
            q_spoken = f"{crop.title()} பயிருக்கு என்ன செய்ய வேண்டும்?"
        elif lang == "kn":
            q_spoken = f"{crop.title()} ಬೆಳೆಗೆ ಸೂಕ್ತ ಸಲಹೆ ನೀಡಿ."
        elif lang == "ml":
            q_spoken = f"{crop.title()} കൃഷിക്ക് ആവശ്യമായ നിർദ്ദേശം തരൂ."

        questions.append({
            "id": f"voice_q_{count:03d}",
            "modality": "voice",
            "language": lang,
            "state": st,
            "district": dist,
            "crop": crop,
            "crop_stage": "vegetative",
            "topic": "spoken_farmer_inquiry",
            "difficulty": "basic",
            "question": q_spoken,
            "expected_intent": intent,
            "required_context": "digital_twin_and_voice_pipeline",
            "expected_evidence_type": "sarvam_stt_tts_and_tools",
            "safety_sensitive": safe,
            "live_data_required": live,
            "vision_required": False
        })

    return questions[:100]


def generate_image_scenarios():
    """
    Scans real image files from data/organized/vision/ across all 10 supported crop model families:
    Tomato, Banana, Guava, Corn/Maize, Apple, Chilli, Cucumber/Pumpkin, Sugarcane, Potato, Rice.
    Generates exactly 100 realistic reviewer image diagnostic scenarios.
    """
    crop_dirs = {
        "potato": "potato_diseases",
        "guava": "guava_diseases",
        "tomato": "tomato_diseases",
        "banana": "banana_diseases",
        "chilli": "chilli_diseases",
        "corn_maize": "corn_maize_diseases",
        "apple": "apple_diseases",
        "cucumber_pumpkin": "cucumber_pumpkin_diseases",
        "sugarcane": "sugarcane_diseases",
        "rice": "rice_diseases"
    }

    scenarios = []
    count = 0

    # Collect up to 10 sample images per crop family
    for crop, folder in crop_dirs.items():
        folder_path = os.path.join(VISION_DIR, folder)
        found_imgs = []
        if os.path.isdir(folder_path):
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    if f.lower().endswith((".jpg", ".jpeg", ".png")):
                        found_imgs.append(os.path.join(root, f))
                        if len(found_imgs) >= 12:
                            break
                if len(found_imgs) >= 12:
                    break

        selected_imgs = found_imgs[:10]
        for img_idx, img_path in enumerate(selected_imgs):
            count += 1
            rel_path = os.path.relpath(img_path, BASE_DIR).replace("\\", "/")
            label = os.path.basename(os.path.dirname(img_path))
            
            # Formulate realistic user query attached to image
            lang = LANGUAGES[count % len(LANGUAGES)]
            questions_by_lang = {
                "en": f"What is wrong with this {crop.replace('_', ' ')} leaf? Is it serious?",
                "te": f"ఈ ఆకులో కనిపిస్తున్న తెగులు లేదా సమస్య ఏమిటి? దీనికి నివారణ చెప్పండి.",
                "hi": f"इस पत्ती में क्या बीमारी है? कृपया इसका सही उपचार बताएं।",
                "ta": f"இந்த இலையில் என்ன நோய் தாக்கியுள்ளது? தீர்வு என்ன?",
                "kn": f"ಈ ಎಲೆಯಲ್ಲಿ ಕಾಣುತ್ತಿರುವ ರೋಗವೇನು? ಪರಿಹಾರ ತಿಳಿಸಿ.",
                "ml": f"ഈ ഇലയിൽ കാണുന്ന രോഗലക്ഷണം എന്താണ്? എന്താണ് ചെയ്യേണ്ടത്?"
            }
            q_text = questions_by_lang.get(lang, questions_by_lang["en"])
            
            # Special test scenarios: crop conflict detection (e.g. potato uploaded on chilli farm)
            is_conflict_test = (crop in ["potato", "guava"] and img_idx < 3)
            registered_farm_crop = "chilli" if is_conflict_test else crop

            scenarios.append({
                "id": f"image_scenario_{count:03d}",
                "modality": "image",
                "image_path": rel_path,
                "crop": crop,
                "registered_farm_crop": registered_farm_crop,
                "true_label": label,
                "question": q_text,
                "language": lang,
                "region": "Andhra Pradesh / Telangana" if count % 2 == 0 else "Punjab / Uttar Pradesh",
                "intent": "IMAGE_DIAGNOSIS",
                "expected_model_family": crop,
                "is_cross_crop_conflict_test": is_conflict_test,
                "expected_behavior": "detect_potato_not_chilli" if crop == "potato" else (
                    "detect_guava_not_chilli" if crop == "guava" else "crop_specific_diagnosis"
                ),
                "safety_sensitive": True if "rice" in crop else False,
                "live_data_required": False,
                "vision_required": True
            })

    # Pad or trim to exactly 100
    return scenarios[:100]

def main():
    print("Generating 300 Reviewer Evaluation Scenarios...")
    chat_qs = generate_chat_questions()
    voice_qs = generate_voice_questions()
    image_qs = generate_image_scenarios()

    print(f"Chat Questions: {len(chat_qs)}")
    print(f"Voice Questions: {len(voice_qs)}")
    print(f"Image Scenarios: {len(image_qs)}")
    total = len(chat_qs) + len(voice_qs) + len(image_qs)
    print(f"Total Reviewer Scenarios: {total}")

    chat_path = os.path.join(OUT_DIR, "chat_questions.json")
    voice_path = os.path.join(OUT_DIR, "voice_questions.json")
    image_path = os.path.join(OUT_DIR, "image_questions.json")

    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_qs, f, indent=2, ensure_ascii=False)
    with open(voice_path, "w", encoding="utf-8") as f:
        json.dump(voice_qs, f, indent=2, ensure_ascii=False)
    with open(image_path, "w", encoding="utf-8") as f:
        json.dump(image_qs, f, indent=2, ensure_ascii=False)

    print("Generated all 3 files successfully in:", OUT_DIR)

if __name__ == "__main__":
    main()

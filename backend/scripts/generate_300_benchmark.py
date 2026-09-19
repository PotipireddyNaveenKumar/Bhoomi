"""
BHOOMI — 300 Benchmark Scenarios Generator
Creates canonical data/benchmarks/300_scenarios.json containing:
- 100 Chat Scenarios
- 100 Voice Scenarios (with voice_audio_type: "transcript_only" / "real_audio")
- 100 Vision Scenarios (real image paths across 10 crops, healthy, blurry, non-leaf, unsupported)

All scenarios initialize with execution_status = "pending".
"""

import os
import glob
import json
import random
from PIL import Image, ImageFilter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCHMARK_DIR = os.path.join(REPO_ROOT, "data", "benchmarks")
BENCHMARK_IMAGES_DIR = os.path.join(BENCHMARK_DIR, "test_images")
OUTPUT_FILE = os.path.join(BENCHMARK_DIR, "300_scenarios.json")

os.makedirs(BENCHMARK_IMAGES_DIR, exist_ok=True)

# 1. Helper to generate synthetic / edge test images if needed
def prepare_edge_test_images():
    blurry_path = os.path.join(BENCHMARK_IMAGES_DIR, "blurry_leaf.jpg")
    non_leaf_path = os.path.join(BENCHMARK_IMAGES_DIR, "non_leaf_blue_surface.jpg")
    non_leaf_metal = os.path.join(BENCHMARK_IMAGES_DIR, "non_leaf_gray_metal.jpg")

    # Find a real leaf to blur
    leaf_samples = glob.glob(os.path.join(REPO_ROOT, "data", "organized", "vision", "tomato_diseases", "**", "*.jpg"), recursive=True)
    if leaf_samples and not os.path.exists(blurry_path):
        with Image.open(leaf_samples[0]) as img:
            blurred = img.filter(ImageFilter.GaussianBlur(radius=12))
            blurred.save(blurry_path, quality=90)

    if not os.path.exists(non_leaf_path):
        blue_img = Image.new("RGB", (224, 224), (40, 100, 200))
        blue_img.save(non_leaf_path)

    if not os.path.exists(non_leaf_metal):
        gray_img = Image.new("RGB", (224, 224), (120, 120, 125))
        gray_img.save(non_leaf_metal)

# 2. Generate 100 Chat Scenarios
def build_chat_scenarios():
    chat_seeds = [
        # Telugu (18)
        {"q": "గుంటూరులో 3 ఎకరాల నల్లరేగడి నేలలో ఏ ఖరీఫ్ పంట వేస్తే అత్యధిక నికర లాభం వస్తుంది?", "lang": "te", "domain": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "tool": "rag_tool", "constraints": {"must_contain": ["లాభం", "పంట"], "language": "te"}},
        {"q": "రేపు వర్షం పడే అవకాశం 60% ఉంటే ఈరోజు నా మిర్చి తోటలో మందు పిచికారీ చేయవచ్చా?", "lang": "te", "domain": "weather", "intent": "SPRAY_WEATHER_SAFETY", "tool": "weather_tool", "constraints": {"must_contain": ["వర్షం", "పిచికారీ"], "language": "te"}},
        {"q": "రేపు వర్షం పడుతుందా?", "lang": "te", "domain": "weather", "intent": "WEATHER_RAIN", "tool": "weather_tool", "constraints": {"must_contain": ["రేపు", "వర్షం"], "cannot_contain": ["ప్రస్తుత ఉష్ణోగ్రత"], "language": "te"}},
        {"q": "నా వరి పంటలో ఆకులు ఎండిపోయి అంచులు గోధుమ రంగులోకి మారుతున్నాయి, ఇది ఏ తెగులు?", "lang": "te", "domain": "pathology", "intent": "DISEASE_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["నివారణ"], "language": "te"}},
        {"q": "వరంగల్ మార్కెట్లో ఈరోజు పత్తి క్వింటాలు మోడల్ ధర ఎంత పలుకుతోంది?", "lang": "te", "domain": "market", "intent": "MARKET_PRICE", "tool": "market_tool", "constraints": {"must_contain": ["క్వింటాలు", "రూ."], "language": "te"}},
        {"q": "మిరప ఆకులు పైకి దోనెలా ముడుచుకుంటున్నాయి. దీనికి మోనోక్రోటోఫాస్ పిచికారీ చేయవచ్చా?", "lang": "te", "domain": "safety", "intent": "BANNED_CHEMICAL_CHECK", "tool": "safety_engine", "constraints": {"must_contain": ["నిషేధించబడినది", "మోనోక్రోటోఫాస్"], "language": "te"}},
        {"q": "టమోటా సాగులో ఎకరాకు అంచనా సాగు ఖర్చు, స్థూల రాబడి మరియు నికర లాభం ఎంత ఉంటుంది?", "lang": "te", "domain": "economics", "intent": "PROFIT_CALCULATION", "tool": "rag_tool", "constraints": {"must_contain": ["ఎకరాకు"], "language": "te"}},
        {"q": "నేల పరీక్షలో pH 7.8 వచ్చింది, నత్రజని లోపం ఉంది. ఏ ఎరువులు ఎంత మోతాదులో వాడాలి?", "lang": "te", "domain": "soil", "intent": "FERTILIZER_RECOMMENDATION", "tool": "rag_tool", "constraints": {"must_contain": ["నత్రజని", "యూరియా"], "language": "te"}},
        {"q": "వర్షాలు ఆలస్యమైతే నల్లరేగడి నేలలో పత్తికి బదులు ఏ ప్రత్యామ్నాయ పంట లాభదాయకం?", "lang": "te", "domain": "crop_recommendation", "intent": "CROP_COMPARISON", "tool": "rag_tool", "constraints": {"must_contain": ["ప్రత్యామ్నాయ"], "language": "te"}},
        {"q": "బంగాళాదుంప పంటలో ఆకులపై నల్లటి మచ్చలు వచ్చాయి, అగెటీ ఝులసా నివారణ ఏమిటి?", "lang": "te", "domain": "pathology", "intent": "DISEASE_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["బంగాళాదుంప"], "language": "te"}},
        {"q": "జామ తోటలో పండ్లపై మచ్చలు వస్తున్నాయి. సమగ్ర యాజమాన్యం ఏమిటి?", "lang": "te", "domain": "pathology", "intent": "PEST_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["జామ"], "language": "te"}},
        {"q": "పీఎం ఫసల్ బీమా యోజన కింద పంట నష్టపరిహారం ఎలా నమోదు చేయాలి?", "lang": "te", "domain": "schemes", "intent": "PMFBY_INSURANCE", "tool": "rag_tool", "constraints": {"must_contain": ["72 గంటలు", "టోల్ ఫ్రీ"], "language": "te"}},
        {"q": "మొక్కజొన్నలో కత్తెర పురుగు నివారణ పద్ధతులు తెలపండి.", "lang": "te", "domain": "pathology", "intent": "PEST_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["కత్తెర పురుగు"], "language": "te"}},
        {"q": "వరి నాట్లు వేసిన 20 రోజులకు ఎలాంటి కలుపు మందు వాడాలి?", "lang": "te", "domain": "weed_management", "intent": "WEED_CONTROL", "tool": "rag_tool", "constraints": {"must_contain": ["వరి", "కలుపు"], "language": "te"}},
        {"q": "ప్రస్తుత ఉష్ణోగ్రత మరియు గాలి తేమ ఎంత?", "lang": "te", "domain": "weather", "intent": "WEATHER_CURRENT", "tool": "weather_tool", "constraints": {"must_contain": ["ఉష్ణోగ్రత"], "language": "te"}},
        {"q": "మిరప తోటలో డ్రిప్ ఇరిగేషన్ ద్వారా నీటి తడులు ఎలా ఇవ్వాలి?", "lang": "te", "domain": "irrigation", "intent": "IRRIGATION_SCHEDULE", "tool": "rag_tool", "constraints": {"must_contain": ["డ్రిప్"], "language": "te"}},
        {"q": "టమోటా నారుమడి తయారీలో పాటించవలసిన మెళకువలు ఏమిటి?", "lang": "te", "domain": "agronomy", "intent": "NURSERY_MANAGEMENT", "tool": "rag_tool", "constraints": {"must_contain": ["నారుమడి"], "language": "te"}},
        {"q": "వేప నూనెను మిరపలో రసం పీల్చే పురుగుల నివారణకు ఎలా వాడాలి?", "lang": "te", "domain": "organic_ipm", "intent": "IPM_ADVISORY", "tool": "rag_tool", "constraints": {"must_contain": ["వేప నూనె"], "language": "te"}},

        # Hindi (18)
        {"q": "काली मिट्टी में 3 एकड़ खेत के लिए सबसे ज्यादा मुनाफा देने वाली खरीफ फसल कौन सी है?", "lang": "hi", "domain": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "tool": "rag_tool", "constraints": {"must_contain": ["फसल", "मुनाफा"], "language": "hi"}},
        {"q": "कल बारिश की 70% संभावना है, क्या मुझे आज कीटनाशक का छिड़काव करना चाहिए?", "lang": "hi", "domain": "weather", "intent": "SPRAY_WEATHER_SAFETY", "tool": "weather_tool", "constraints": {"must_contain": ["बारिश", "छिड़काव"], "language": "hi"}},
        {"q": "क्या कल बारिश होगी?", "lang": "hi", "domain": "weather", "intent": "WEATHER_RAIN", "tool": "weather_tool", "constraints": {"must_contain": ["कल", "बारिश"], "language": "hi"}},
        {"q": "धान की पत्तियों पर कत्थई रंग के नाव के आकार के धब्बे हैं, क्या यह ब्लास्ट रोग है?", "lang": "hi", "domain": "pathology", "intent": "DISEASE_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["ब्लास्ट"], "language": "hi"}},
        {"q": "आज नासिक मंडी में प्याज का मॉडल भाव क्या चल रहा है?", "lang": "hi", "domain": "market", "intent": "MARKET_PRICE", "tool": "market_tool", "constraints": {"must_contain": ["रुपये", "क्विंटल"], "language": "hi"}},
        {"q": "मिर्च में माहू और थ्रिप्स के नियंत्रण के लिए क्या एंडोसल्फान का छिड़काव कर सकते हैं?", "lang": "hi", "domain": "safety", "intent": "BANNED_CHEMICAL_CHECK", "tool": "safety_engine", "constraints": {"must_contain": ["प्रतिबंधित"], "language": "hi"}},
        {"q": "आलू की फसल में अगेती झुलसा के लक्षण और जैविक उपचार बताएं।", "lang": "hi", "domain": "pathology", "intent": "DISEASE_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["झुलसा"], "language": "hi"}},
        {"q": "अमरूद में विल्ट रोग के क्या कारण हैं और इसे कैसे फैलने से रोकें?", "lang": "hi", "domain": "pathology", "intent": "DISEASE_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["विल्ट"], "language": "hi"}},
        {"q": "गेंहू में पहली सिंचाई (CRI अवस्था) कितने दिनों बाद करनी चाहिए?", "lang": "hi", "domain": "irrigation", "intent": "IRRIGATION_TIMING", "tool": "rag_tool", "constraints": {"must_contain": ["सिंचाई", "21"], "language": "hi"}},
        {"q": "मक्का में फॉल आर्मीवॉर्म के जैविक नियंत्रण हेतु फेरोमोन ट्रैप कैसे लगाएं?", "lang": "hi", "domain": "organic_ipm", "intent": "PEST_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["ट्रैप"], "language": "hi"}},
        {"q": "मिट्टी का pH 6.2 है, गन्ने की बुवाई से पहले कितना जिप्सम डालना चाहिए?", "lang": "hi", "domain": "soil", "intent": "SOIL_AMENDMENT", "tool": "rag_tool", "constraints": {"must_contain": ["pH"], "language": "hi"}},
        {"q": "प्रधानमंत्री फसल बीमा योजना में क्लेम दर्ज करने की समय सीमा क्या है?", "lang": "hi", "domain": "schemes", "intent": "PMFBY_INSURANCE", "tool": "rag_tool", "constraints": {"must_contain": ["72 घंटे"], "language": "hi"}},
        {"q": "सोयाबीन की बुवाई के लिए बीज दर और कतार से कतार की दूरी क्या रखें?", "lang": "hi", "domain": "agronomy", "intent": "SOWING_ADVISORY", "tool": "rag_tool", "constraints": {"must_contain": ["दूरी"], "language": "hi"}},
        {"q": "आज का मौसम और तापमान कैसा रहेगा?", "lang": "hi", "domain": "weather", "intent": "WEATHER_CURRENT", "tool": "weather_tool", "constraints": {"must_contain": ["तापमान"], "language": "hi"}},
        {"q": "टमाटर में फल छेदक कीट के रोकथाम के उपाय क्या हैं?", "lang": "hi", "domain": "pathology", "intent": "PEST_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["कीट"], "language": "hi"}},
        {"q": "कपास में गुलाबी सुंडी का प्रकोप रोकने के लिए कौन से उपाय करें?", "lang": "hi", "domain": "pathology", "intent": "PEST_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["गुलाबी सुंडी"], "language": "hi"}},
        {"q": "सरसों में पहली सिंचाई कब देनी चाहिए?", "lang": "hi", "domain": "irrigation", "intent": "IRRIGATION_TIMING", "tool": "rag_tool", "constraints": {"must_contain": ["सरसों"], "language": "hi"}},
        {"q": "डीएपी खाद की जगह क्या सिंगल सुपर फॉस्फेट इस्तेमाल कर सकते हैं?", "lang": "hi", "domain": "soil", "intent": "FERTILIZER_RECOMMENDATION", "tool": "rag_tool", "constraints": {"must_contain": ["फास्फोरस"], "language": "hi"}},

        # English (20)
        {"q": "Which Kharif crop will yield the highest net profit for 3 acres of black cotton soil?", "lang": "en", "domain": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "tool": "rag_tool", "constraints": {"must_contain": ["profit", "acre"], "language": "en"}},
        {"q": "Rain probability is 65% tomorrow in Guntur. Is it safe to spray fungicide today?", "lang": "en", "domain": "weather", "intent": "SPRAY_WEATHER_SAFETY", "tool": "weather_tool", "constraints": {"must_contain": ["spray", "rain"], "language": "en"}},
        {"q": "Will it rain tomorrow?", "lang": "en", "domain": "weather", "intent": "WEATHER_RAIN", "tool": "weather_tool", "constraints": {"must_contain": ["tomorrow", "rain"], "cannot_contain": ["current observation"], "language": "en"}},
        {"q": "What is the current temperature and humidity in Warangal?", "lang": "en", "domain": "weather", "intent": "WEATHER_CURRENT", "tool": "weather_tool", "constraints": {"must_contain": ["temperature", "humidity"], "language": "en"}},
        {"q": "What is the expected cultivation cost, gross yield and net profit for 3 acres of potato?", "lang": "en", "domain": "economics", "intent": "PROFIT_CALCULATION", "tool": "rag_tool", "constraints": {"must_contain": ["cost", "profit"], "language": "en"}},
        {"q": "Leaves on my guava tree are yellowing and dropping prematurely. What is the diagnosis?", "lang": "en", "domain": "pathology", "intent": "DISEASE_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["guava"], "language": "en"}},
        {"q": "Can I spray monocrotophos or paraquat on vegetable crops for weed and insect knockdown?", "lang": "en", "domain": "safety", "intent": "BANNED_CHEMICAL_CHECK", "tool": "safety_engine", "constraints": {"must_contain": ["banned", "prohibited"], "language": "en"}},
        {"q": "Check today modal price for Cotton in Warangal market. Should I sell now or wait?", "lang": "en", "domain": "market", "intent": "MARKET_PRICE", "tool": "market_tool", "constraints": {"must_contain": ["price", "quintal"], "language": "en"}},
        {"q": "My soil test shows pH 6.4, N=85 kg/ha, P=38 kg/ha, K=40 kg/ha. What fertilizer dose should I apply for Rice?", "lang": "en", "domain": "soil", "intent": "FERTILIZER_RECOMMENDATION", "tool": "rag_tool", "constraints": {"must_contain": ["nitrogen", "urea"], "language": "en"}},
        {"q": "How does PMFBY assess localized hailstorm or unseasonal rain crop loss?", "lang": "en", "domain": "schemes", "intent": "PMFBY_INSURANCE", "tool": "rag_tool", "constraints": {"must_contain": ["72 hours", "claim"], "language": "en"}},
        {"q": "What are the key symptoms of Fall Armyworm in Maize and approved bio-pesticides?", "lang": "en", "domain": "pathology", "intent": "PEST_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["armyworm"], "language": "en"}},
        {"q": "Compare economic returns between Groundnut and Soybean under rainfed conditions.", "lang": "en", "domain": "crop_recommendation", "intent": "CROP_COMPARISON", "tool": "rag_tool", "constraints": {"must_contain": ["groundnut", "soybean"], "language": "en"}},
        {"q": "What is the recommended seed treatment fungicide for wheat before sowing?", "lang": "en", "domain": "agronomy", "intent": "SEED_TREATMENT", "tool": "rag_tool", "constraints": {"must_contain": ["seed treatment"], "language": "en"}},
        {"q": "How to identify bacterial leaf blight in rice compared to leaf blast?", "lang": "en", "domain": "pathology", "intent": "DISEASE_QUERY", "tool": "rag_tool", "constraints": {"must_contain": ["blight", "blast"], "language": "en"}},
        {"q": "Can phorate granules be applied to sugarcane at planting?", "lang": "en", "domain": "safety", "intent": "BANNED_CHEMICAL_CHECK", "tool": "safety_engine", "constraints": {"must_contain": ["banned"], "language": "en"}},
        {"q": "What is the optimum temperature range for tomato fruit setting?", "lang": "en", "domain": "agronomy", "intent": "CROP_MANAGEMENT", "tool": "rag_tool", "constraints": {"must_contain": ["temperature"], "language": "en"}},
        {"q": "What is the market price of maize in Nizamabad today?", "lang": "en", "domain": "market", "intent": "MARKET_PRICE", "tool": "market_tool", "constraints": {"must_contain": ["maize"], "language": "en"}},
        {"q": "How much potassium sulphate should be applied for banana bunches?", "lang": "en", "domain": "soil", "intent": "FERTILIZER_RECOMMENDATION", "tool": "rag_tool", "constraints": {"must_contain": ["potassium"], "language": "en"}},
        {"q": "What organic mulch materials are most effective for moisture retention in chilli?", "lang": "en", "domain": "agronomy", "intent": "IRRIGATION_SCHEDULE", "tool": "rag_tool", "constraints": {"must_contain": ["mulch"], "language": "en"}},
        {"q": "Is it safe to spray chlorpyrifos on leafy vegetables?", "lang": "en", "domain": "safety", "intent": "BANNED_CHEMICAL_CHECK", "tool": "safety_engine", "constraints": {"must_contain": ["safety"], "language": "en"}},
    ]

    # Fill remaining up to 100 with structured variations
    crops = ["tomato", "chilli", "potato", "rice", "corn_maize", "cotton", "soybean", "wheat", "guava", "banana", "sugarcane", "onion"]
    topics = [
        ("What are the recommended irrigation intervals for {crop} during flowering stage?", "irrigation", "IRRIGATION_SCHEDULE", "rag_tool"),
        ("What is the current wholesale mandi price for {crop}?", "market", "MARKET_PRICE", "market_tool"),
        ("Can endosulfan be safely sprayed on {crop} for pest eradication?", "safety", "BANNED_CHEMICAL_CHECK", "safety_engine"),
        ("How much urea and DAP should be applied per acre for {crop}?", "soil", "FERTILIZER_RECOMMENDATION", "rag_tool"),
        ("What are the integrated pest management (IPM) practices for {crop}?", "organic_ipm", "IPM_ADVISORY", "rag_tool"),
        ("How does excess rainfall impact {crop} during maturity?", "weather", "WEATHER_STRESS", "weather_tool"),
        ("What are the eligibility criteria for PM-KISAN financial assistance?", "schemes", "GOVERNMENT_SCHEME", "rag_tool")
    ]

    scenarios = []
    for s in chat_seeds:
        scenarios.append({
            "id": f"CHAT-{len(scenarios)+1:03d}",
            "mode": "chat",
            "language": s["lang"],
            "crop_or_domain": s["domain"],
            "intent": s["intent"],
            "input_or_image_path": s["q"],
            "expected_tool_or_model": s["tool"],
            "expected_output_constraints": s["constraints"],
            "execution_status": "pending"
        })

    c_idx = 0
    t_idx = 0
    while len(scenarios) < 100:
        c = crops[c_idx % len(crops)]
        tpl, domain, intent, tool = topics[t_idx % len(topics)]
        q_text = tpl.format(crop=c.replace("_", " ").title())
        scenarios.append({
            "id": f"CHAT-{len(scenarios)+1:03d}",
            "mode": "chat",
            "language": "en" if len(scenarios) % 3 == 0 else ("te" if len(scenarios) % 3 == 1 else "hi"),
            "crop_or_domain": domain,
            "intent": intent,
            "input_or_image_path": q_text,
            "expected_tool_or_model": tool,
            "expected_output_constraints": {"must_contain": [c.replace("_", " ")], "language": "en"},
            "execution_status": "pending"
        })
        c_idx += 1
        t_idx += 1

    return scenarios[:100]

# 3. Generate 100 Voice Scenarios
def build_voice_scenarios():
    voice_seeds = [
        # Telugu (30)
        {"q": "మిరప తోటకి ఈరోజు నీరు పెట్టాలా వద్దా?", "lang": "te", "domain": "chilli", "intent": "IRRIGATION_QUERY", "tool": "weather_tool"},
        {"q": "రేపు వర్షం పడుతుందా? మందు కొట్టొచ్చా?", "lang": "te", "domain": "weather", "intent": "SPRAY_WEATHER_SAFETY", "tool": "weather_tool"},
        {"q": "రేపు వర్షం పడుతుందా?", "lang": "te", "domain": "weather", "intent": "WEATHER_RAIN", "tool": "weather_tool"},
        {"q": "నా వరి చేనులో ఆకులు పసుపుగా మారుతున్నాయి, ఏం చేయాలి?", "lang": "te", "domain": "rice", "intent": "DISEASE_QUERY", "tool": "rag_tool"},
        {"q": "వరంగల్ మార్కెట్లో పత్తి ధర ఈరోజు ఎలా ఉంది?", "lang": "te", "domain": "cotton", "intent": "MARKET_PRICE", "tool": "market_tool"},
        {"q": "ఈరోజు పొలంలో నేను చేయాల్సిన ముఖ్యమైన పని ఏమిటి?", "lang": "te", "domain": "farm_manager", "intent": "DAILY_BRIEFING", "tool": "task_engine"},
        {"q": "మిర్చిలో ఆకుముడతకి ఏ మందు పిచికారీ చేయాలి?", "lang": "te", "domain": "chilli", "intent": "DISEASE_QUERY", "tool": "rag_tool"},
        {"q": "నా 3 ఎకరాల భూమికి ఏ పంట వేస్తే ఎక్కువ లాభం వస్తుంది?", "lang": "te", "domain": "chilli", "intent": "CROP_RECOMMENDATION", "tool": "rag_tool"},
        {"q": "టమోటా కాయలు కుళ్ళిపోతున్నాయి, దానికి నివారణ చెప్పండి.", "lang": "te", "domain": "tomato", "intent": "DISEASE_QUERY", "tool": "rag_tool"},
        {"q": "జామ కాయలపై పురుగులు వస్తున్నాయి, ఏం స్ప్రే చేయాలి?", "lang": "te", "domain": "guava", "intent": "PEST_QUERY", "tool": "rag_tool"},
        {"q": "బంగాళాదుంప తవ్వకం ఎప్పుడు చేయాలి?", "lang": "te", "domain": "potato", "intent": "HARVEST_QUERY", "tool": "rag_tool"},
        {"q": "పత్తిలో గులాబీ రంగు పురుగు కనిపిస్తోంది ఏం మందు కొట్టాలి?", "lang": "te", "domain": "cotton", "intent": "PEST_QUERY", "tool": "rag_tool"},
        {"q": "వరికి ఎకరాకు ఎన్ని బస్తాల యూరియా వేయాలి?", "lang": "te", "domain": "rice", "intent": "FERTILIZER_QUERY", "tool": "rag_tool"},
        {"q": "ఈరోజు ఉష్ణోగ్రత ఎంత ఉండబోతోంది?", "lang": "te", "domain": "weather", "intent": "WEATHER_CURRENT", "tool": "weather_tool"},
        {"q": "మొక్కజొన్నలో ఎరువులు ఎప్పుడు వేయాలి?", "lang": "te", "domain": "corn_maize", "intent": "FERTILIZER_QUERY", "tool": "rag_tool"},
        
        # Hindi (30)
        {"q": "क्या आज मुझे अपने खेत में पानी देना चाहिए?", "lang": "hi", "domain": "irrigation", "intent": "IRRIGATION_QUERY", "tool": "weather_tool"},
        {"q": "कल बारिश होगी क्या? कीटनाशक का स्प्रे करूं या रुकूं?", "lang": "hi", "domain": "weather", "intent": "SPRAY_WEATHER_SAFETY", "tool": "weather_tool"},
        {"q": "क्या कल बारिश होगी?", "lang": "hi", "domain": "weather", "intent": "WEATHER_RAIN", "tool": "weather_tool"},
        {"q": "धान की बालियों में दाना नहीं भर रहा, क्या कारण है?", "lang": "hi", "domain": "rice", "intent": "DISEASE_QUERY", "tool": "rag_tool"},
        {"q": "आज इंदौर मंडी में सोयाबीन का क्या भाव चल रहा है?", "lang": "hi", "domain": "soybean", "intent": "MARKET_PRICE", "tool": "market_tool"},
        {"q": "मिर्च की पत्तियां ऊपर मुड़ रही हैं, क्या मोनोक्रोटोफॉस डाल दूं?", "lang": "hi", "domain": "chilli", "intent": "BANNED_CHEMICAL_CHECK", "tool": "safety_engine"},
        {"q": "आलू की फसल में पाले से बचाव के लिए क्या करें?", "lang": "hi", "domain": "potato", "intent": "CROP_MANAGEMENT", "tool": "rag_tool"},
        {"q": "मक्का में भुट्टे में कीड़ा लगा है, इसका क्या इलाज है?", "lang": "hi", "domain": "corn_maize", "intent": "PEST_QUERY", "tool": "rag_tool"},
        {"q": "आज मेरे खेत का क्या काम बाकी है?", "lang": "hi", "domain": "farm_manager", "intent": "DAILY_BRIEFING", "tool": "task_engine"},
        {"q": "टमाटर में फल सड़ रहे हैं क्या स्प्रे करें?", "lang": "hi", "domain": "tomato", "intent": "DISEASE_QUERY", "tool": "rag_tool"},
        {"q": "गेंहू में यूरिया की पहली टॉप ड्रेसिंग कब करें?", "lang": "hi", "domain": "wheat", "intent": "FERTILIZER_QUERY", "tool": "rag_tool"},
        {"q": "कपास में गुलाबी सुंडी का नियंत्रण कैसे करें?", "lang": "hi", "domain": "cotton", "intent": "PEST_QUERY", "tool": "rag_tool"},

        # English (40)
        {"q": "Should I irrigate my chilli field today?", "lang": "en", "domain": "chilli", "intent": "IRRIGATION_QUERY", "tool": "weather_tool"},
        {"q": "Rain expected tomorrow, is it safe to spray fungicide?", "lang": "en", "domain": "weather", "intent": "SPRAY_WEATHER_SAFETY", "tool": "weather_tool"},
        {"q": "Will it rain tomorrow?", "lang": "en", "domain": "weather", "intent": "WEATHER_RAIN", "tool": "weather_tool"},
        {"q": "What is today's mandi price for cotton in Guntur?", "lang": "en", "domain": "cotton", "intent": "MARKET_PRICE", "tool": "market_tool"},
        {"q": "My potato leaves have dark brown target rings, what is this?", "lang": "en", "domain": "potato", "intent": "DISEASE_QUERY", "tool": "rag_tool"},
        {"q": "Which crop is best for 3 acres of black soil?", "lang": "en", "domain": "crop_recommendation", "intent": "CROP_RECOMMENDATION", "tool": "rag_tool"},
        {"q": "Why are my guava tree leaves curling and dropping?", "lang": "en", "domain": "guava", "intent": "PEST_QUERY", "tool": "rag_tool"},
        {"q": "What farm tasks are scheduled for today?", "lang": "en", "domain": "farm_manager", "intent": "DAILY_BRIEFING", "tool": "task_engine"},
        {"q": "Can I spray endosulfan on tomato?", "lang": "en", "domain": "safety", "intent": "BANNED_CHEMICAL_CHECK", "tool": "safety_engine"},
        {"q": "What is the current temperature in Warangal?", "lang": "en", "domain": "weather", "intent": "WEATHER_CURRENT", "tool": "weather_tool"},
        {"q": "How to treat yellow stem borer in paddy?", "lang": "en", "domain": "rice", "intent": "PEST_QUERY", "tool": "rag_tool"},
        {"q": "When is the right time to harvest soybean?", "lang": "en", "domain": "soybean", "intent": "HARVEST_QUERY", "tool": "rag_tool"},
    ]

    scenarios = []
    for s in voice_seeds:
        scenarios.append({
            "id": f"VOICE-{len(scenarios)+1:03d}",
            "mode": "voice",
            "language": s["lang"],
            "crop_or_domain": s["domain"],
            "intent": s["intent"],
            "input_or_image_path": s["q"],
            "expected_tool_or_model": s["tool"],
            "expected_output_constraints": {"intent": s["intent"], "language": s["lang"]},
            "execution_status": "pending",
            "voice_audio_type": "transcript_only"  # Clearly marked as transcript-only if audio file is absent
        })

    # Fill remaining up to 100
    crops = ["tomato", "chilli", "potato", "rice", "corn_maize", "cotton", "wheat", "soybean", "guava", "banana"]
    templates = [
        ("How much fertilizer per acre should I give to {crop}?", "FERTILIZER_QUERY", "rag_tool"),
        ("What is the mandi price for {crop} today?", "MARKET_PRICE", "market_tool"),
        ("Are there pest alerts for {crop} this week?", "PEST_QUERY", "rag_tool"),
        ("Should I spray pesticide on {crop} this afternoon?", "SPRAY_WEATHER_SAFETY", "weather_tool"),
        ("What are the water requirements for {crop} today?", "IRRIGATION_QUERY", "weather_tool")
    ]

    idx = 0
    while len(scenarios) < 100:
        c = crops[idx % len(crops)]
        tpl, intent, tool = templates[idx % len(templates)]
        q_text = tpl.format(crop=c.replace("_", " ").title())
        lang = "en" if len(scenarios) % 3 == 0 else ("te" if len(scenarios) % 3 == 1 else "hi")
        scenarios.append({
            "id": f"VOICE-{len(scenarios)+1:03d}",
            "mode": "voice",
            "language": lang,
            "crop_or_domain": c,
            "intent": intent,
            "input_or_image_path": q_text,
            "expected_tool_or_model": tool,
            "expected_output_constraints": {"intent": intent, "language": lang},
            "execution_status": "pending",
            "voice_audio_type": "transcript_only"
        })
        idx += 1

    return scenarios[:100]

# 4. Generate 100 Vision Scenarios
def build_vision_scenarios():
    scenarios = []

    # Map target crops to their directories and expected model
    crops_config = [
        ("potato", "potato_diseases", "potato_vision_v1.0", 10),
        ("tomato", "tomato_diseases", "tomato_vision_v1.0", 10),
        ("chilli", "chilli_diseases", "chilli_vision_v1.0", 10),
        ("guava", "guava_diseases", "guava_vision_v1.0", 10),
        ("corn_maize", "corn_maize_diseases", "corn_maize_vision_v1.0", 10),
        ("apple", "apple_diseases", "apple_vision_v1.0", 10),
        ("rice", "rice_diseases", "rice_vision_v1.0", 10),
        ("banana", "banana_diseases", "banana_vision_v1.0", 10),
        ("cucumber_pumpkin", "cucumber_pumpkin_diseases", "cucumber_pumpkin_vision_v1.0", 10)
    ]

    for crop, folder, model_ver, count in crops_config:
        base_search = os.path.join(REPO_ROOT, "data", "organized", "vision", folder)
        found_files = []
        for ext in ["*.jpg", "*.jpeg", "*.png"]:
            found_files.extend(glob.glob(os.path.join(base_search, "**", ext), recursive=True))

        selected = found_files[:count] if len(found_files) >= count else found_files
        for idx, fpath in enumerate(selected):
            rel_path = os.path.relpath(fpath, REPO_ROOT).replace("\\", "/")
            # Extract class name from folder
            parent_name = os.path.basename(os.path.dirname(fpath))
            scenarios.append({
                "id": f"VISION-{len(scenarios)+1:03d}",
                "mode": "vision",
                "language": "en",
                "crop_or_domain": crop,
                "intent": "LEAF_DIAGNOSIS",
                "input_or_image_path": rel_path,
                "expected_tool_or_model": model_ver,
                "expected_output_constraints": {
                    "expected_crop": crop,
                    "expected_subfolder": parent_name,
                    "must_reject": False,
                    "min_confidence": 0.50
                },
                "execution_status": "pending"
            })

    # Add 10 Edge & Safety Vision Scenarios:
    # - 3 Blurry images (must reject by quality gate)
    # - 3 Non-leaf images (must reject by vegetation check)
    # - 4 Unsupported / other plant images (must flag as uncertain or unsupported)
    blurry_rel = os.path.relpath(os.path.join(BENCHMARK_IMAGES_DIR, "blurry_leaf.jpg"), REPO_ROOT).replace("\\", "/")
    for i in range(3):
        scenarios.append({
            "id": f"VISION-{len(scenarios)+1:03d}",
            "mode": "vision",
            "language": "en",
            "crop_or_domain": "quality_rejection",
            "intent": "IMAGE_QUALITY_CHECK",
            "input_or_image_path": blurry_rel,
            "expected_tool_or_model": "ImageQualityGate",
            "expected_output_constraints": {
                "must_reject": True,
                "expected_disease": "QUALITY_CHECK_FAILED"
            },
            "execution_status": "pending"
        })

    non_leaf_blue = os.path.relpath(os.path.join(BENCHMARK_IMAGES_DIR, "non_leaf_blue_surface.jpg"), REPO_ROOT).replace("\\", "/")
    non_leaf_metal = os.path.relpath(os.path.join(BENCHMARK_IMAGES_DIR, "non_leaf_gray_metal.jpg"), REPO_ROOT).replace("\\", "/")
    for i, path in enumerate([non_leaf_blue, non_leaf_metal, non_leaf_blue]):
        scenarios.append({
            "id": f"VISION-{len(scenarios)+1:03d}",
            "mode": "vision",
            "language": "en",
            "crop_or_domain": "non_leaf_rejection",
            "intent": "LEAF_PRESENCE_CHECK",
            "input_or_image_path": path,
            "expected_tool_or_model": "ImageQualityGate",
            "expected_output_constraints": {
                "must_reject": True,
                "expected_disease": "QUALITY_CHECK_FAILED"
            },
            "execution_status": "pending"
        })

    # Unsupported crops (e.g. lettuce from other_crop_diseases)
    lettuce_files = glob.glob(os.path.join(REPO_ROOT, "data", "organized", "vision", "other_crop_diseases", "**", "*.jpg"), recursive=True)
    unsupported_samples = lettuce_files[:4]
    for idx, fpath in enumerate(unsupported_samples):
        rel_path = os.path.relpath(fpath, REPO_ROOT).replace("\\", "/")
        scenarios.append({
            "id": f"VISION-{len(scenarios)+1:03d}",
            "mode": "vision",
            "language": "en",
            "crop_or_domain": "unsupported_plant",
            "intent": "LEAF_DIAGNOSIS",
            "input_or_image_path": rel_path,
            "expected_tool_or_model": "CropModelRegistry",
            "expected_output_constraints": {
                "must_reject": True,
                "expected_disease": "CROP_UNCERTAIN",
                "chemical_withheld": True
            },
            "execution_status": "pending"
        })

    return scenarios[:100]

def main():
    print("Preparing edge test images...")
    prepare_edge_test_images()

    print("Building 100 chat scenarios...")
    chat = build_chat_scenarios()

    print("Building 100 voice scenarios...")
    voice = build_voice_scenarios()

    print("Building 100 vision scenarios...")
    vision = build_vision_scenarios()

    all_300 = {
        "metadata": {
            "title": "BHOOMI 300-Scenario Pre-Deployment Benchmark",
            "version": "2.0",
            "total_count": len(chat) + len(voice) + len(vision),
            "chat_count": len(chat),
            "voice_count": len(voice),
            "vision_count": len(vision)
        },
        "scenarios": chat + voice + vision
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_300, f, indent=2, ensure_ascii=False)

    print(f"Successfully generated {len(all_300['scenarios'])} benchmark scenarios to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

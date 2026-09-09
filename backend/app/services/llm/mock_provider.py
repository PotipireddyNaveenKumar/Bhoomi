import json
from typing import List, Dict, Any, Optional
from app.services.llm.base import LLMProvider, LLMResponse, ToolCall

class MockLLMProvider(LLMProvider):
    """
    Intelligent Multilingual Mock LLM Provider for unit tests, offline development,
    and predictable agent testing without live cloud API dependencies.
    Provides authentic agricultural reasoning across English, Telugu, Hindi, Tamil, Kannada, and Malayalam
    adhering to the caring brother / well-wisher persona.
    """

    @staticmethod
    def _detect_lang(text: str, system_prompt: str) -> str:
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
        sys_lower = system_prompt.lower()
        if "telugu" in sys_lower or "language: te" in sys_lower:
            return "te"
        if "hindi" in sys_lower or "language: hi" in sys_lower:
            return "hi"
        if "tamil" in sys_lower or "language: ta" in sys_lower:
            return "ta"
        if "kannada" in sys_lower or "language: kn" in sys_lower:
            return "kn"
        if "malayalam" in sys_lower or "language: ml" in sys_lower:
            return "ml"
        return "en"

    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        last_message = messages[-1]["content"].lower() if messages else ""
        lang = self._detect_lang(last_message, system_prompt)

        # 1. Weekly Schedule & Priorities
        if any(w in last_message for w in ["week", "వారం", "हफ्ते", "வாரம்", "ವಾರ", "ആഴ്ച"]):
            resp_by_lang = {
                "te": "గుంటూరులోని మీ 3 ఎకరాల మిర్చి తోట పూత/కాయ దశలో ఉంది. ఈ వారం ముఖ్యమైన పనులు:\n1. మధ్యాహ్నం వర్ష సూచన ఉన్నందున ఉపరితల తడిని వాయిదా వేయండి\n2. ఆకుల అడుగున తామర పురుగుల ఉనికిని గమనించండి\n3. వాతావరణం అనుకూలించినప్పుడు 19:19:19 పోషక పిచికారీ చేపట్టండి.",
                "hi": "गुंटूर में आपकी 3 एकड़ मिर्च की फसल के लिए इस सप्ताह के मुख्य कार्य:\n1. दोपहर में बारिश की संभावना के कारण सिंचाई टालें\n2. थ्रिप्स कीट की रोकथाम के लिए पत्तियों की जांच करें\n3. गुरुवार सुबह संतुलित पोषक तत्व का छिड़काव करें।",
                "en": "For your 3-acre chilli crop in Guntur, here is what to focus on this week:\n1. Hold off on watering because showers are on the way.\n2. Keep an eye under the leaves for any small pests.\n3. Spray balanced nutrients on Thursday morning."
            }
            return LLMResponse(
                content=resp_by_lang.get(lang, resp_by_lang["en"]),
                tool_calls=[ToolCall(tool_name="get_current_weather", arguments={"location": "Guntur"})],
                provider="mock"
            )

        # 2. Fertilizer & Nutrition
        elif any(w in last_message for w in ["fertilizer", "urea", "dose", "nutrient", "ఎరువు", "పోషకాలు", "खाद", "உரம்", "ಗೊಬ್ಬರ", "വളം"]):
            if any(w in last_message for w in ["rice", "paddy", "వరి", "धान", "நெல்", "ಭತ್ತ"]):
                resp_by_lang = {
                    "te": "వరి పంట నమూనాలు ప్రస్తుతం పరిశోధన దశలో ఉన్నాయి. వరిపై రైతులకు రసాయన స్ప్రే సిఫార్సులు అనుమతించబడవు.",
                    "hi": "चावल की फसल के मॉडल वर्तमान में अनुसंधान चरण में हैं। रासायनिक छिड़काव की सिफारिश प्रतिबंधित है।",
                    "en": "Rice crop models are currently designated as RESEARCH_ONLY pending physical field validation. Farmer-facing chemical spraying prescriptions are restricted for rice."
                }
                return LLMResponse(content=resp_by_lang.get(lang, resp_by_lang["en"]), tool_calls=None, provider="mock")

            if "soil" not in last_message and "chilli" not in last_message and "మిర్చి" not in last_message:
                resp_by_lang = {
                    "te": "సరియైన ఎరువుల మోతాదును సిఫార్సు చేయడానికి: మీరు ఏ పంట సాగు చేస్తున్నారు, పంట వయస్సు ఎంత, మరియు మీ నేల రకం ఏమిటి?",
                    "hi": "सटीक खाद खुराक के लिए: आप कौन सी फसल उगा रहे हैं, फसल की उम्र क्या है, और आपकी मिट्टी का प्रकार क्या है?",
                    "en": "To give you the exact fertilizer dosage, brother: Which crop are you growing, how many days old is it, and what kind of soil do you have?"
                }
                return LLMResponse(content=resp_by_lang.get(lang, resp_by_lang["en"]), tool_calls=None, provider="mock")
            else:
                resp_by_lang = {
                    "te": "నల్లరేగడి నేలలో 45 రోజుల మిర్చి పంటకు: ఎకరాకు 25 కేజీల యూరియా మరియు 15 కేజీల ఎంఓపీని నేలలో తగినంత తేమ ఉన్నప్పుడు వేయండి.",
                    "hi": "काली मिट्टी में 45 दिन की मिर्च की फसल के लिए: प्रति एकड़ 25 किलोग्राम यूरिया और 15 किलोग्राम एमओपी पर्याप्त नमी में दें।",
                    "en": "For your 45-day chilli crop on black soil: Apply twenty-five kilos of urea and fifteen kilos of MOP per acre near the roots while the soil has good moisture."
                }
                return LLMResponse(
                    content=resp_by_lang.get(lang, resp_by_lang["en"]),
                    tool_calls=[ToolCall(tool_name="fertilizer_recommendation", arguments={"crop_name": "Chilli", "soil_type": "black", "crop_stage": "vegetative", "nitrogen": 40.0, "phosphorus": 20.0, "potassium": 30.0})],
                    provider="mock"
                )

        # 3. Market & Mandi Price
        elif any(k in last_message for k in ["price", "mandi", "market", "sell", "rate", "modal", "దర", "ధర", "మార్కెట్", "అమ్మ", "దाम", "मंडी", "भाव", "बेच", "விலை", "ಬೆಲೆ", "വില"]):
            resp_by_lang = {
                "te": "గుంటూరు మార్కెట్ యార్డులో తేజ మిర్చి ప్రస్తుత మోడల్ ధర క్వింటాలుకు ₹12,000. రవాణా ఖర్చు ₹150 తీసేస్తే మీ చేతికి ₹11,850 వస్తుంది.",
                "hi": "गुंटूर मंडी में तेजा मिर्च का भाव ₹12,000 प्रति क्विंटल है। ₹150 भाड़ा काटकर आपके हाथ में ₹11,850 प्रति क्विंटल आएंगे।",
                "en": "In Guntur mandi today, Teja chilli is selling at ₹12,000 a quintal. After about ₹150 for transport, you'll take home ₹11,850 per quintal."
            }
            return LLMResponse(
                content=resp_by_lang.get(lang, resp_by_lang["en"]),
                tool_calls=[ToolCall(tool_name="get_mandi_prices", arguments={"commodity": "Chilli", "location": "Guntur", "state": "Andhra Pradesh"})],
                provider="mock"
            )

        # 4. Yield Prediction
        elif any(k in last_message for k in ["yield", "production", "దిగుబడి", "దిగుబడి ఎంత", "पैदावार", "उपज", "மகசூல்"]):
            resp_by_lang = {
                "te": "ఆంధ్రప్రదేశ్‌లోని 3 ఎకరాల మిర్చి తోటలో ఎకరాకు సుమారు 10.5 క్వింటాళ్ల దిగుబడి (మొత్తం: ~31.5 క్వింటాళ్లు) వచ్చే అవకాశం ఉంది.",
                "hi": "आंध्र प्रदेश में 3 एकड़ मिर्च से प्रति एकड़ लगभग 10.5 क्विंटल (कुल: ~31.5 क्विंटल) पैदावार मिलने का अनुमान है।",
                "en": "For your 3 acres of chilli, you can look forward to about 10.5 quintals per acre, giving roughly 31.5 quintals in total."
            }
            return LLMResponse(
                content=resp_by_lang.get(lang, resp_by_lang["en"]),
                tool_calls=[ToolCall(tool_name="yield_prediction", arguments={"crop_name": "Chilli", "area_acres": 3.0, "state": "Andhra Pradesh", "season": "Kharif"})],
                provider="mock"
            )

        # 5. Profit & Economics
        elif any(k in last_message for k in ["profit", "revenue", "margin", "economics", "roi", "లాభ", "లాభాల", "ఆదాయం", "దిగుబడి లాభం", "मुनाफा", "आमदनी", "లాபம்", "ಲಾಭ", "లాഭം"]):
            resp_by_lang = {
                "te": "మీ 3 ఎకరాల మిర్చి తోటలో మొత్తం 30 క్వింటాళ్లు వస్తే, ₹12,000 ధర వద్ద ₹3,60,000 ఆదాయం వస్తుంది. ఖర్చులు ₹2,10,000 తీసివేస్తే ₹1,50,000 నికర లాభం మిగులుతుంది.",
                "hi": "3 एकड़ मिर्च से ₹12,000 के भाव पर कुल ₹3,60,000 की बिक्री होगी। ₹2,10,000 खर्च के बाद ₹1,50,000 का साफ मुनाफा रहेगा।",
                "en": "For 3 acres yielding 10 quintals per acre at ₹12,000: Total sales will be ₹3,60,000. After ₹2,10,000 in costs, you'll make about ₹1,50,000 in clean profit."
            }
            return LLMResponse(
                content=resp_by_lang.get(lang, resp_by_lang["en"]),
                tool_calls=[ToolCall(tool_name="calculate_profit", arguments={"crop_name": "Chilli", "area_acres": 3.0, "expected_yield_quintals_per_acre": 10.0, "expected_market_price_per_quintal": 12000.0, "cultivation_cost_total": 70000.0})],
                provider="mock"
            )

        # 6. Weather & Rainfall
        elif any(k in last_message for k in ["weather", "rain", "temperature", "forecast", "వాతావరణ", "వర్ష", "मौसम", "बारिश", "வானிலை", "हवामान", "കാലാവസ്ഥ"]):
            resp_by_lang = {
                "te": "గుంటూరులో ప్రస్తుత ఉష్ణోగ్రత 31.5°C. మధ్యాహ్నం 40% వర్ష సూచన ఉంది, కాబట్టి ఈరోజు నీరు పెట్టడం ఆపండి. వర్షం తర్వాత నేల చూద్దాం.",
                "hi": "गुंटूर में अभी तापमान 31.5°C है। दोपहर में 40% बारिश की संभावना है, इसलिए आज पानी देने से बचें। बारिश के बाद मिट्टी की नमी देखकर तय करेंगे।",
                "en": "In Guntur right now, it's 31.5°C with about a 40% chance of rain this afternoon. Hold off on watering today and let's see how much rain falls."
            }
            return LLMResponse(
                content=resp_by_lang.get(lang, resp_by_lang["en"]),
                tool_calls=[ToolCall(tool_name="get_current_weather", arguments={"location": "Guntur"})],
                provider="mock"
            )

        # 7. Crop Recommendation & Soil Suitability
        elif any(k in last_message for k in ["crop", "soil", "black soil", "recommend crop", "best crop", "నల్ల రేగడి", "నల్లరేగడి", "పంట", "काली मिट्टी", "फसल", "கரிசல் மண்", "ಕಪ್ಪು ಮಣ್ಣು"]):
            resp_by_lang = {
                "te": "గుంటూరులోని నల్లరేగడి నేల తేమను చాలా బాగా పట్టి ఉంచుతుంది. మీకు అత్యంత అనుకూలమైన లాభదాయక పంటలు: 1. తేజ మిర్చి 2. పత్తి 3. శనగలు.",
                "hi": "गुंटूर की काली मिट्टी नमी बहुत अच्छे से बनाए रखती है। आपके लिए सबसे अच्छी मुनाफेदार फसलें: 1. तेजा मिर्च 2. कपास 3. चना।",
                "en": "Deep black cotton soil in Guntur holds moisture really well. The most profitable crops for your land are: Chilli (Teja variety), Cotton, and Bengal Gram."
            }
            return LLMResponse(
                content=resp_by_lang.get(lang, resp_by_lang["en"]),
                tool_calls=[ToolCall(tool_name="crop_recommendation", arguments={"nitrogen": 90.0, "phosphorus": 42.0, "potassium": 43.0, "ph": 6.5, "rainfall": 200.0, "temperature": 25.0, "humidity": 80.0})],
                provider="mock"
            )

        # 8. Agronomic Knowledge / RAG Search
        elif any(k in last_message for k in ["rotation", "chlorosis", "ipm", "integrated pest", "pest management", "మార్పిడి", "చక్ర"]):
            resp_by_lang = {
                "te": "పంట మార్పిడి మరియు సమగ్ర తెగుళ్ల యాజమాన్యంపై ధృవీకరించబడిన పరిశోధనా సమాచారం అందుబాటులో ఉంది.",
                "hi": "फसल चक्र और एकीकृत कीट प्रबंधन पर सत्यापित अनुसंधान जानकारी उपलब्ध है।",
                "en": "Verified agricultural research evidence from ICAR guidelines confirms significant benefits for soil health and pest break."
            }
            return LLMResponse(
                content=resp_by_lang.get(lang, resp_by_lang["en"]),
                tool_calls=[ToolCall(tool_name="search_agricultural_rag", arguments={"query": last_message, "crop": "chilli"})],
                provider="mock"
            )

        # 9. Greetings
        elif any(k in last_message for k in ["hello", "hi", "hey", "namaste", "namaskaram", "నమస్కారం", "నమస్తే", "नमस्ते", "வணக்கம்", "നമസ്കാര", "നമസ്കാരം"]):
            resp_by_lang = {
                "te": "నమస్కారం రమేష్ గారు! మీతో మాట్లాడటం సంతోషం. గుంటూరులోని మీ 3 ఎకరాల మిర్చి తోట చక్కగా ఉంది. ఈరోజు పనులు, వాతావరణం లేదా మార్కెట్ ధరల గురించి తెలుసుకోవాలా?",
                "hi": "नमस्ते रमेश जी! आपसे बात करके अच्छा लगा। गुंटूर में आपकी 3 एकड़ मिर्च की फसल बहुत अच्छी चल रही है। आज मैं आपकी क्या मदद करूँ?",
                "en": "Namaste Ramesh! Good to speak with you. Your 3-acre chilli crop in Guntur is growing well. How can I help you today — want to check the weather, today's work, or mandi rates?"
            }
            return LLMResponse(content=resp_by_lang.get(lang, resp_by_lang["en"]), tool_calls=None, provider="mock")

        # 10. Conversational Fallback (Honest agricultural farm manager response)
        else:
            resp_by_lang = {
                "te": "రమేష్ గారు, మీ ప్రశ్నను అర్థం చేసుకున్నాను. మీ 3 ఎకరాల మిర్చి తోటలో వాతావరణం మరియు మార్కెట్ ధరలను పర్యవేక్షిస్తున్నాను. నేటి పనులు లేదా వాతావరణం గురించి మాట్లాడదామా?",
                "hi": "रमेश जी, मैंने आपकी बात समझी। आपकी 3 एकड़ मिर्च की फसल के लिए मौसम और मंडी भाव पर मेरी नजर है। क्या आज के काम या मौसम का हाल देखना चाहते हैं?",
                "en": "Ramesh, I hear you. I'm keeping a close eye on the weather and mandi rates for your 3 acres of chilli. Would you like to check today's priorities or the weather forecast?"
            }
            return LLMResponse(content=resp_by_lang.get(lang, resp_by_lang["en"]), tool_calls=None, provider="mock")

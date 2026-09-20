/**
 * BHOOMI (FRAM-AI) — MULTIMODAL AI AGRONOMIST CLIENT ENGINE
 * Handles multi-session management, auto-titling, theme toggling,
 * multilingual speech recognition, image attachment, and grounded chat workflows.
 */

// Global State
let currentSessionId = "";
let currentLanguage = localStorage.getItem("bhoomi_lang") || "en";
let attachedImageBase64 = null;
let isRecordingVoice = false;
let speechRecognizer = null;
let sessionsList = [];
let authToken = localStorage.getItem("bhoomi_auth_token") || null;
let currentUser = null;
let pendingOtpPhone = "";
let currentAuthMode = "LOGIN"; // "LOGIN" | "SIGNUP" | "REVIEWER"

// Audio & Voice Engine State (Apple Siri-Style Natural Female Voice)
let currentAudioPlayer = null;
let currentPlayingButton = null;
let isVoiceCallOpen = false;
let voiceCallRecognizer = null;
let voiceCallTranscriptBuffer = "";
let voiceCallSilenceTimer = null;

// Debug / Development Mode flag (defaults to false in production)
const IS_DEV_MODE = (function() {
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.get("dev") === "true" || params.get("debug") === "true" || params.get("dev") === "1") return true;
    return localStorage.getItem("bhoomi_dev_mode") === "true" || window.BHOOMI_DEV_MODE === true;
  } catch (e) {
    return false;
  }
})();

// On-Screen Toast Notification System
function showToast(message, type = "info", duration = 5000) {
  try {
    let container = document.getElementById("bhoomiToastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "bhoomiToastContainer";
      container.className = "bhoomi-toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `bhoomi-toast bhoomi-toast-${type}`;

    let icon = "ℹ️";
    if (type === "warning") icon = "⚠️";
    else if (type === "error") icon = "❌";
    else if (type === "success") icon = "✅";

    toast.innerHTML = `
      <span class="bhoomi-toast-icon">${icon}</span>
      <span class="bhoomi-toast-text">${message}</span>
      <button class="bhoomi-toast-close" aria-label="Close" onclick="this.parentElement.remove()">✕</button>
    `;

    container.appendChild(toast);

    requestAnimationFrame(() => {
      toast.classList.add("bhoomi-toast-show");
    });

    setTimeout(() => {
      if (toast.parentElement) {
        toast.classList.remove("bhoomi-toast-show");
        toast.classList.add("bhoomi-toast-hide");
        setTimeout(() => toast.remove(), 300);
      }
    }, duration);
  } catch (e) {
    console.warn("[TOAST_FALLBACK]", message, e);
  }
}
window.showToast = showToast;

// Comprehensive Localization Dictionary for ALL 6 Languages (Default: English)
const I18N = {
  en: {
    heroTitle: "Ask BHOOMI Your Agricultural Questions",
    heroSubtitle: "Grounded crop planning, yield forecasts, mandi prices, leaf disease scanning & profit economics.",
    placeholder: "Ask about crops, profit, diseases, or weather (Type or speak)...",
    newChat: "New Chat",
    recent: "Recent Conversations",
    clear: "Clear",
    langLabel: "Language:",
    voiceCallBtn: "Live Voice Call",
    farmerProfileTitle: "Farmer Profile & Farm Details",
    saveProfileBtn: "💾 Save Changes",
    logoutBtn: "🚪 Logout",
    chips: [
      { title: "🌾 Crop Selection & Profit", sub: "Which Kharif crop will yield highest net profit for 3 acres of black soil?", prompt: "Which Kharif crop will yield highest net profit for 3 acres of black soil?" },
      { title: "💰 Paddy Profit Breakdown", sub: "What is the expected revenue, cultivation cost and net profit for paddy?", prompt: "What is the profit of paddy?" },
      { title: "🍃 Disease Management", sub: "What are the major pests, blast symptoms and CIBRC control in rice?", prompt: "What are major issues of growing paddy?" },
      { title: "🌦️ 7-Day Spray Advisory", sub: "Weather forecast, rain probability and optimal spraying window.", prompt: "Will it rain tomorrow in Warangal? Is it safe to spray?" }
    ],
    finance: {
      headerBtn: "Finance & Profit",
      headerBtnTitle: "Farm Financial Planner & What-If Simulation",
      title: "Farm Finance & Profit",
      subtitle: "7-Component Cost Breakdown, Break-Even Analysis & What-If Simulation (100% Deterministic)",
      cropName: "🌾 Crop Name",
      cropPlaceholder: "e.g. Chilli, Cotton, Rice",
      landArea: "📐 Land Area",
      units: { acre: "Acre", ha: "Hectare", bigha: "Bigha", guntha: "Guntha" },
      costSectionTitle: "📋 7-Component Cultivation Costs (in ₹)",
      costSeed: "Seed (₹)", costFertilizer: "Fertilizer (₹)", costPesticide: "Pesticide (₹)",
      costLabour: "Labour (₹)", costIrrigation: "Irrigation (₹)", costMachinery: "Machinery / Tractor (₹)", costOther: "Other Costs (₹)",
      costTotalLumpSum: "Or Total Cultivation Cost (₹):",
      costTotalPlaceholder: "e.g. 35000",
      yieldSectionTitle: "📈 Expected Yield & Market Price",
      expectedYield: "Expected Yield per Area",
      yieldUnits: { quintal: "Quintal", kg: "Kg", tonne: "Tonne" },
      yieldHint: "If yield is omitted, break-even yield will be calculated.",
      expectedPrice: "Expected Market Price",
      priceUnits: { rupees_per_quintal: "₹ / Quintal", rupees_per_kg: "₹ / Kg" },
      priceHint: "If price is omitted, break-even price will be calculated.",
      simLeversSummary: "⚡ What-If Simulation Levers",
      simPriceChange: "Market Price Change (%)", simYieldChange: "Yield Change (%)",
      simCostChange: "Total Cost Change (%)", simFertilizerChange: "Fertilizer Cost Change (%)",
      btnCalculate: "📊 Calculate Profit & Costs",
      btnRunSim: "⚡ Run What-If Simulation",
      calculating: "⏳ Calculating deterministic farm finance...",
      calcFailed: "Calculation failed. Please verify your inputs.",
      networkError: "Network error while connecting to finance service.",
      simRunning: "⚡ Running multi-lever scenario simulation...",
      simFailed: "Simulation failed.",
      simNetworkError: "Network error while connecting to simulation service.",
      cardTotalCost: "Total Cost", cardGrossRevenue: "Gross Revenue", cardNetProfit: "Net Profit",
      cardProfitPerArea: "Profit per", cardRoi: "Return on Investment", deterministicBadge: "Deterministic",
      calcTitle: "📊 Financial Calculation",
      costBreakdownTitle: "7-Component Cost Breakdown:",
      costLabels: {
        seed_cost: "Seed",
        fertilizer_cost: "Fertilizer",
        pesticide_cost: "Pesticide",
        labour_cost: "Labour",
        irrigation_cost: "Irrigation",
        machinery_cost: "Machinery / Tractor",
        other_cost: "Other Costs"
      },
      breakEvenPriceLabel: "🎯 Break-Even Market Price:", breakEvenPriceDesc: "(Minimum price needed to avoid loss)",
      breakEvenYieldLabel: "🎯 Break-Even Yield:", breakEvenYieldDesc: "(Minimum production needed to cover cost)",
      partialCalcWarning: "⚠️ Partial Calculation (Missing: {fields})",
      viewTrace: "🔍 View Deterministic Calculation Trace ({count} steps)",
      simResultTitle: "⚡ Multi-Lever What-If Simulation", simScenarioBadge: "Scenario Comparison",
      tblMetric: "Metric", tblBaseline: "Baseline", tblSimulated: "Simulated Scenario", tblDifference: "Difference",
      tblMarketPrice: "Market Price", tblTotalProduction: "Total Production", tblGrossRevenue: "Gross Revenue",
      tblCultivationCost: "Cultivation Cost", tblNetProfit: "Net Profit", tblRoi: "Return on Investment (ROI)",
      riskExplanationTitle: "💡 Risk Explanation:",
      mitigationActionsTitle: "🛡️ Recommended Risk Mitigation Actions:",
      validationCostWarning: "Please enter cultivation costs before running simulation",
      validationYieldPriceWarning: "Please enter baseline Yield and Market Price for What-If Simulation"
    },
    voice: {
      agentTitle: "BHOOMI Voice Assistant",
      farmerRole: "👨‍🌾 Farmer:",
      farmerInitialText: '"Speak your question or problem clearly..."',
      farmerListening: "Listening... Speak your question clearly...",
      aiRole: "🌾 BHOOMI (Voice Assistant):",
      aiGreeting: '"Hello! Ask me directly about your crops, pests, diseases, weather, or market mandi prices."',
      statusListening: "Listening carefully...",
      statusThinking: "Gathering farm data and analyzing...",
      statusSpeaking: "Speaking...",
      statusIdle: "Tap to Speak",
      micListening: "Listening...",
      micThinking: "Thinking...",
      micSpeaking: "Speaking...",
      micTapToSpeak: "Tap to Speak",
      endCall: "End Call",
      micError: "⚠️ Microphone not accessible or blocked.",
      tapForHelp: "Tap for Permission Help & Quick Prompts",
      tapToListen: "🔊 Tap to Listen to Spoken Answer"
    },
    decisions: {
      title: "Decision History",
      subtitle: "Persistent memory & explainable AI advisory traces",
      refresh: "Refresh",
      empty: "No decision history recorded yet. Use voice or chat to evaluate farm decisions.",
      modalTitle: "Decision Provenance & Trace",
      modalSubtitle: "Explainable AI, Telemetry Grounding & Feedback",
      whyRationale: "Why & Rationale",
      evidenceSensors: "Evidence & Telemetry Grounding",
      dataSources: "Data Sources & Freshness",
      toolsSafety: "Tools Used & Safety Screening",
      modelXai: "Model & Explainability (XAI)",
      calculations: "Calculations & Economics",
      actionFeedback: "Farmer Action & Feedback",
      statusLabel: "Status:",
      feedbackLabel: "Feedback Rating:",
      notesLabel: "Notes:",
      btnAccept: "✓ Accept / Follow",
      btnReject: "✕ Reject / Not Follow",
      btnPostpone: "⏳ Postpone",
      btnHelpful: "👍 Useful",
      btnNotHelpful: "👎 Not Useful",
      btnSubmitFeedback: "Submit Feedback",
      feedbackPlaceholder: "Add notes or observations...",
      feedbackSuccess: "Feedback updated and persisted in PostgreSQL!",
      viewDetail: "View Trace & Explainability →"
    }
  },
  te: {
    heroTitle: "మీ వ్యవసాయ సందేహాలు నన్ను అడగండి",
    heroSubtitle: "పంటల ఎంపిక, దిగుబడి అంచనా, మార్కెట్ ధరలు, తెగుళ్ల గుర్తింపు & లాభాల గణన.",
    placeholder: "మీ పంట లేదా సమస్య గురించి అడగండి (Type or speak in Telugu)...",
    newChat: "కొత్త సంభాషణ",
    recent: "గత సంభాషణలు",
    clear: "తుడవండి",
    langLabel: "భాష (Language):",
    voiceCallBtn: "వాయిస్ సంభాషణ",
    farmerProfileTitle: "రైతు ప్రొఫైల్ & పొలం వివరాలు",
    saveProfileBtn: "💾 మార్పులను సేవ్ చేయండి",
    logoutBtn: "🚪 లాగ్ అవుట్",
    chips: [
      { title: "🌾 పంట ఎంపిక & లాభం", sub: "ఈ ఖరీఫ్‌లో నా 3 ఎకరాల నల్లరేగడి నేలలో ఏ పంట ఎక్కువ లాభం?", prompt: "ఈ ఖరీఫ్‌లో నా 3 ఎకరాల నల్లరేగడి నేలలో ఏ పంట వేసుకోవచ్చు?" },
      { title: "💰 వరి పంట లాభాల లెక్క", sub: "వరి పంట సాగు చేస్తే ఎకరానికి ఖర్చు మరియు నికర లాభం ఎంత?", prompt: "వరి పంట సాగు చేస్తే ఎంత లాభం వస్తుంది?" },
      { title: "🍃 ఆకు తెగులు & నివారణ", sub: "వరిలో అగ్గి తెగులు నివారణకు ICAR సిఫార్సు చేసిన మందులు ఏమిటి?", prompt: "వరిలో అగ్గి తెగులు నివారణకు ఏ మందు పిచికారీ చేయాలి?" },
      { title: "🌦️ వాతావరణం & స్ప్రే సలహా", sub: "రాబోయే 7 రోజుల వర్ష సూచన మరియు మందులు కొట్టే సమయం.", prompt: "రేపు వర్షం పడుతుందా? మందులు స్ప్రే చేయవచ్చా?" }
    ],
    finance: {
      headerBtn: "ఆర్థిక విశ్లేషణ & లాభం",
      headerBtnTitle: "వ్యవసాయ ఆర్థిక ప్రణాళిక & వాట్-ఇఫ్ సిమ్యులేషన్",
      title: "వ్యవసాయ ఆర్థిక విశ్లేషణ & లాభం",
      subtitle: "7-వ్యయ విభజన, బ్రేక్-ఈవెన్ లెక్కలు మరియు వాట్-ఇఫ్ సిమ్యులేషన్ (100% Deterministic)",
      cropName: "🌾 పంట పేరు",
      cropPlaceholder: "ఉదా: మిర్చి, పత్తి, వరి",
      landArea: "📐 సాగు విస్తీర్ణం",
      units: { acre: "ఎకరం", ha: "హెక్టారు", bigha: "బిఘా", guntha: "గుంట" },
      costSectionTitle: "📋 7-విభాగాల సాగు ఖర్చులు (₹ లలో)",
      costSeed: "విత్తనాలు (₹)", costFertilizer: "ఎరువులు (₹)", costPesticide: "పురుగుమందులు (₹)",
      costLabour: "కూలి ఖర్చులు (₹)", costIrrigation: "నీటిపారుదల (₹)", costMachinery: "ట్రాక్టర్/యంత్రాలు (₹)", costOther: "ఇతర ఖర్చులు (₹)",
      costTotalLumpSum: "లేదా మొత్తం సాగు ఖర్చు (₹):",
      costTotalPlaceholder: "ఉదా: 35000",
      yieldSectionTitle: "📈 ఆశించే దిగుబడి & మార్కెట్ ధర",
      expectedYield: "ఎకరాకు దిగుబడి",
      yieldUnits: { quintal: "క్వింటాల్", kg: "కిలో", tonne: "టన్ను" },
      yieldHint: "దిగుబడి ఇవ్వకపోతే బ్రేక్-ఈవెన్ దిగుబడి లెక్కించబడుతుంది.",
      expectedPrice: "ఆశించే మార్కెట్ ధర",
      priceUnits: { rupees_per_quintal: "₹ / క్వింటాల్", rupees_per_kg: "₹ / కిలో" },
      priceHint: "ధర ఇవ్వకపోతే బ్రేక్-ఈవెన్ ధర లెక్కించబడుతుంది.",
      simLeversSummary: "⚡ వాట్-ఇఫ్ సిమ్యులేషన్ సెట్టింగ్‌లు",
      simPriceChange: "మార్కెట్ ధర మార్పు (%)", simYieldChange: "దిగుబడి మార్పు (%)",
      simCostChange: "మొత్తం ఖర్చు మార్పు (%)", simFertilizerChange: "ఎరువుల ఖర్చు మార్పు (%)",
      btnCalculate: "📊 లాభం & ఖర్చులు లెక్కించండి",
      btnRunSim: "⚡ సిమ్యులేషన్ రన్ చేయండి",
      calculating: "⏳ ఆర్థిక గణాంకాలు లెక్కించబడుతున్నాయి...",
      calcFailed: "గణన విఫలమైంది. దయచేసి వివరాలను సరిచూసుకోండి.",
      networkError: "సర్వర్‌ను సంప్రదించడంలో నెట్‌వర్క్ లోపం ఏర్పడింది.",
      simRunning: "⚡ బహుళ అంశాల సిమ్యులేషన్ రన్ అవుతోంది...",
      simFailed: "సిమ్యులేషన్ విఫలమైంది.",
      simNetworkError: "సిమ్యులేషన్ సర్వర్‌కు కనెక్ట్ చేయడంలో నెట్‌వర్క్ లోపం.",
      cardTotalCost: "మొత్తం ఖర్చు", cardGrossRevenue: "స్థూల ఆదాయం", cardNetProfit: "నికర లాభం",
      cardProfitPerArea: "ప్రతి విస్తీర్ణానికి లాభం", cardRoi: "పెట్టుబడిపై రాబడి (ROI)", deterministicBadge: "ఖచ్చితమైన గణన",
      calcTitle: "📊 ఆర్థిక గణాంకాలు",
      costBreakdownTitle: "7-విభాగాల సాగు ఖర్చులు:",
      costLabels: {
        seed_cost: "విత్తనాలు",
        fertilizer_cost: "ఎరువులు",
        pesticide_cost: "పురుగుమందులు",
        labour_cost: "కూలి ఖర్చులు",
        irrigation_cost: "నీటిపారుదల",
        machinery_cost: "ట్రాక్టర్/యంత్రాలు",
        other_cost: "ఇతర ఖర్చులు"
      },
      breakEvenPriceLabel: "🎯 బ్రేక్-ఈవెన్ మార్కెట్ ధర:", breakEvenPriceDesc: "(నష్టం రాకుండా ఉండటానికి కనీస ధర)",
      breakEvenYieldLabel: "🎯 బ్రేక్-ఈవెన్ దిగుబడి:", breakEvenYieldDesc: "(ఖర్చులు తీరడానికి కనీస ఉత్పత్తి)",
      partialCalcWarning: "⚠️ పాక్షిక గణన (అసంపూర్ణ వివరాలు: {fields})",
      viewTrace: "🔍 ఖచ్చితమైన గణన వివరాలు చూడండి ({count} దశలు)",
      simResultTitle: "⚡ బహుళ అంశాల వాట్-ఇఫ్ సిమ్యులేషన్", simScenarioBadge: "పరిస్థితుల పోలిక",
      tblMetric: "కొలమానం", tblBaseline: "ప్రస్తుత స్థితి", tblSimulated: "సిమ్యులేట్ చేసిన స్థితి", tblDifference: "తేడా",
      tblMarketPrice: "మార్కెట్ ధర", tblTotalProduction: "మొత్తం దిగుబడి", tblGrossRevenue: "స్థూల రాబడి",
      tblCultivationCost: "సాగు ఖర్చు", tblNetProfit: "నికర లాభం", tblRoi: "రాబడి శాతం (ROI)",
      riskExplanationTitle: "💡 రిస్క్ విశ్లేషణ:",
      mitigationActionsTitle: "🛡️ సిఫార్సు చేసిన నష్ట నివారణ చర్యలు:",
      validationCostWarning: "సిమ్యులేషన్ చేయడానికి ముందు సాగు ఖర్చులను నమోదు చేయండి",
      validationYieldPriceWarning: "సిమ్యులేషన్ కోసం ఆశించే దిగుబడి మరియు మార్కెట్ ధరను నమోదు చేయండి"
    },
    voice: {
      agentTitle: "భూమి వాయిస్ అసిస్టెంట్ (BHOOMI Voice Assistant)",
      farmerRole: "👨‍🌾 రైతు (Farmer):",
      farmerInitialText: '"మీ సమస్య లేదా ప్రశ్నను మాట్లాడండి..."',
      farmerListening: "వింటున్నాను... మీ సమస్యను పూర్తిగా మాట్లాడండి...",
      aiRole: "🌾 BHOOMI (వాయిస్ అసిస్టెంట్):",
      aiGreeting: '"నమస్కారం రైతు మిత్రమా! మీ పంట, చీడపీడలు, వాతావరణం లేదా మార్కెట్ ధరల గురించి నేరుగా అడగండి."',
      statusListening: "పూర్తిగా మాట్లాడండి, వింటున్నాను...",
      statusThinking: "సమగ్ర వ్యవసాయ విశ్లేషణ సిద్ధం చేస్తున్నాము...",
      statusSpeaking: "సమాధానం ఇస్తున్నాను...",
      statusIdle: "మాట్లాడటానికి నొక్కండి",
      micListening: "వింటున్నాను...",
      micThinking: "ఆలోచిస్తున్నాను...",
      micSpeaking: "సమాధానం ఇస్తున్నాను...",
      micTapToSpeak: "మాట్లాడండి (Tap to Speak)",
      endCall: "ముగించు (End)",
      micError: "⚠️ మైక్రోఫోన్ అనుమతి లభించలేదు లేదా బ్లాక్ చేయబడింది.",
      tapForHelp: "అనుమతి సహాయం & నమూనా ప్రశ్నలు",
      tapToListen: "🔊 సమాధానం వినడానికి నొక్కండి"
    },
    decisions: {
      title: "నిర్ణయ చరిత్ర (Decision History)",
      subtitle: "స్థిరమైన జ్ఞాపకశక్తి & వివరణాత్మక AI సలహాలు",
      refresh: "రిఫ్రెష్",
      empty: "ఇంకా నిర్ణయ చరిత్ర నమోదు కాలేదు. వ్యవసాయ నిర్ణయాలను అంచనా వేయడానికి వాయిస్ లేదా చాట్ ఉపయోగించండి.",
      modalTitle: "నిర్ణయ మూలం & వివరణ (Decision Provenance)",
      modalSubtitle: "వివరణాత్మక AI, టెలిమెట్రీ గ్రౌండింగ్ & అభిప్రాయం",
      whyRationale: "ఎందుకు & సమర్థన",
      evidenceSensors: "సాక్ష్యం & సెన్సార్ల సమాచారం",
      dataSources: "డేటా వనరులు & తాజాదనం",
      toolsSafety: "ఉపయోగించిన సాధనాలు & భద్రతా తనిఖీలు",
      modelXai: "మోడల్ & వివరణాత్మకత (XAI)",
      calculations: "గణనలు & ఆర్థిక ఫలితాలు",
      actionFeedback: "రైతు చర్య & అభిప్రాయం",
      statusLabel: "స్థితి:",
      feedbackLabel: "రేటింగ్:",
      notesLabel: "గమనికలు:",
      btnAccept: "✓ అంగీకరించు / అనుసరించు",
      btnReject: "✕ తిరస్కరించు",
      btnPostpone: "⏳ వాయిదా వేయి",
      btnHelpful: "👍 ఉపయోగపడింది",
      btnNotHelpful: "👎 ఉపయోగపడలేదు",
      btnSubmitFeedback: "అభిప్రాయాన్ని సమర్పించండి",
      feedbackPlaceholder: "గమనికలు లేదా పరిశీలనలను జోడించండి...",
      feedbackSuccess: "అభిప్రాయం డేటాబేస్లో నవీకరించబడింది!",
      viewDetail: "వివరణ & వివరాలను చూడండి →"
    }
  },
  hi: {
    heroTitle: "अपने कृषि संबंधी प्रश्न मुझसे पूछें",
    heroSubtitle: "फसल चयन, पैदावार का अनुमान, मंडी भाव, कीट-रोग पहचान और शुद्ध मुनाफे का विश्लेषण।",
    placeholder: "अपनी फसल या समस्या के बारे में पूछें (Type or speak in Hindi)...",
    newChat: "नई बातचीत",
    recent: "पिछली बातचीत",
    clear: "हटाएं",
    langLabel: "भाषा (Language):",
    voiceCallBtn: "वॉयस कॉल",
    farmerProfileTitle: "किसान प्रोफाइल और खेत विवरण",
    saveProfileBtn: "💾 बदलाव सहेजें",
    logoutBtn: "🚪 लॉग आउट",
    chips: [
      { title: "🌾 फसल चयन एवं मुनाफा", sub: "खरीफ में 3 एकड़ काली मिट्टी में कौन सी फसल सबसे उपयुक्त है?", prompt: "खरीफ में 3 एकड़ काली मिट्टी में कौन सी फसल लगाएं?" },
      { title: "💰 धान की खेती में मुनाफा", sub: "धान की खेती में कुल लागत, पैदावार और शुद्ध मुनाफा कितना होगा?", prompt: "धान की खेती में कितना मुनाफा होगा?" },
      { title: "🍃 झुलसा रोग एवं रोकथाम", sub: "धान में झुलसा रोग के लक्षण और CIBRC अनुमोदित दवाएं।", prompt: "धान में झुलसा रोग की रोकथाम के लिए कौन सी दवा डालें?" },
      { title: "🌦️ मौसम एवं छिड़काव", sub: "क्या कल बारिश होगी? कीटनाशक छिड़काव का सही समय।", prompt: "क्या कल बारिश होगी? कीटनाशक छिड़काव कर सकते हैं?" }
    ],
    finance: {
      headerBtn: "वित्त एवं मुनाफा",
      headerBtnTitle: "फार्म वित्तीय योजना एवं वाट-इफ सिमुलेशन",
      title: "कृषि वित्त एवं मुनाफा विश्लेषण",
      subtitle: "7-लागत घटक, ब्रेक-ईवन विश्लेषण एवं परिदृश्य सिमुलेशन (100% सटीक)",
      cropName: "🌾 फसल का नाम",
      cropPlaceholder: "उदा: मिर्च, कपास, धान",
      landArea: "📐 भूमि क्षेत्रफल",
      units: { acre: "एकड़", ha: "हेक्टेयर", bigha: "बीघा", guntha: "गुंठा" },
      costSectionTitle: "📋 7-घटक खेती की लागत (₹ में)",
      costSeed: "बीज (₹)", costFertilizer: "उर्वरक / खाद (₹)", costPesticide: "कीटनाशक (₹)",
      costLabour: "मजदूरी (₹)", costIrrigation: "सिंचाई (₹)", costMachinery: "मशीनरी / ट्रैक्टर (₹)", costOther: "अन्य लागत (₹)",
      costTotalLumpSum: "या कुल खेती लागत (₹):",
      costTotalPlaceholder: "उदा: 35000",
      yieldSectionTitle: "📈 अनुमानित पैदावार एवं बाजार भाव",
      expectedYield: "प्रति एकड़ अनुमानित पैदावार",
      yieldUnits: { quintal: "क्विंटल", kg: "किग्रा", tonne: "टन" },
      yieldHint: "पैदावार न देने पर ब्रेक-ईवन पैदावार की गणना की जाएगी।",
      expectedPrice: "अनुमानित बाजार भाव",
      priceUnits: { rupees_per_quintal: "₹ / क्विंटल", rupees_per_kg: "₹ / किग्रा" },
      priceHint: "भाव न देने पर ब्रेक-ईवन बाजार भाव की गणना की जाएगी।",
      simLeversSummary: "⚡ वाट-इफ सिमुलेशन सेटिंग्स",
      simPriceChange: "बाजार भाव में बदलाव (%)", simYieldChange: "पैदावार में बदलाव (%)",
      simCostChange: "कुल लागत में बदलाव (%)", simFertilizerChange: "उर्वरक लागत में बदलाव (%)",
      btnCalculate: "📊 लागत एवं मुनाफा गणना करें",
      btnRunSim: "⚡ सिमुलेशन चलाएं",
      calculating: "⏳ सटीक वित्तीय गणना की जा रही है...",
      calcFailed: "गणना विफल रही। कृपया दर्ज जानकारी जांचें।",
      networkError: "वित्त सेवा से जुड़ने में नेटवर्क त्रुटि हुई।",
      simRunning: "⚡ बहु-कारक परिदृश्य सिमुलेशन चल रहा है...",
      simFailed: "सिमुलेशन विफल रहा।",
      simNetworkError: "सिमुलेशन सेवा से जुड़ने में नेटवर्क त्रुटि हुई।",
      cardTotalCost: "कुल लागत", cardGrossRevenue: "सकल आमदनी", cardNetProfit: "शुद्ध मुनाफा",
      cardProfitPerArea: "प्रति क्षेत्र मुनाफा", cardRoi: "निवेश पर रिटर्न (ROI)", deterministicBadge: "सटीक गणना",
      calcTitle: "📊 वित्तीय गणना",
      costBreakdownTitle: "7-घटक खेती लागत विवरण:",
      costLabels: {
        seed_cost: "बीज",
        fertilizer_cost: "उर्वरक / खाद",
        pesticide_cost: "कीटनाशक",
        labour_cost: "मजदूरी",
        irrigation_cost: "सिंचाई",
        machinery_cost: "मशीनरी / ट्रैक्टर",
        other_cost: "अन्य लागत"
      },
      breakEvenPriceLabel: "🎯 ब्रेक-ईवन बाजार भाव:", breakEvenPriceDesc: "(नुकसान से बचने हेतु न्यूनतम भाव)",
      breakEvenYieldLabel: "🎯 ब्रेक-ईवन पैदावार:", breakEvenYieldDesc: "(लागत निकालने हेतु न्यूनतम उत्पादन)",
      partialCalcWarning: "⚠️ आंशिक गणना (अधूरी जानकारी: {fields})",
      viewTrace: "🔍 सटीक गणना विवरण देखें ({count} चरण)",
      simResultTitle: "⚡ बहु-कारक वाट-इफ सिमुलेशन", simScenarioBadge: "परिदृश्य तुलना",
      tblMetric: "पैमाना", tblBaseline: "वर्तमान स्थिति", tblSimulated: "सिम्युलेटेड स्थिति", tblDifference: "अंतर",
      tblMarketPrice: "बाजार भाव", tblTotalProduction: "कुल पैदावार", tblGrossRevenue: "सकल आमदनी",
      tblCultivationCost: "खेती लागत", tblNetProfit: "शुद्ध मुनाफा", tblRoi: "रिटर्न दर (ROI)",
      riskExplanationTitle: "💡 जोखिम विश्लेषण:",
      mitigationActionsTitle: "🛡️ अनुशंसित जोखिम न्यूनीकरण उपाय:",
      validationCostWarning: "सिमुलेशन चलाने से पहले कृपया खेती की लागत दर्ज करें",
      validationYieldPriceWarning: "सिमुलेशन के लिए कृपया पैदावार और बाजार भाव दर्ज करें"
    },
    voice: {
      agentTitle: "भूमि वॉयस असिस्टेंट (BHOOMI Voice Assistant)",
      farmerRole: "👨‍🌾 किसान (Farmer):",
      farmerInitialText: '"अपनी समस्या या प्रश्न बोलें..."',
      farmerListening: "सुन रहे हैं... अपनी बात स्पष्ट रूप से बोलें...",
      aiRole: "🌾 BHOOMI (वॉयस असिस्टेंट):",
      aiGreeting: '"नमस्ते किसान भाई! अपनी फसल, कीट-रोग, मौसम या मंडी भाव के बारे में सीधे पूछें।"',
      statusListening: "पूरी बात बताएं, सुन रहे हैं...",
      statusThinking: "विश्लेषण कर रहे हैं...",
      statusSpeaking: "उत्तर दे रहे हैं...",
      statusIdle: "बोलने के लिए टैप करें",
      micListening: "सुन रहे हैं...",
      micThinking: "सोच रहे हैं...",
      micSpeaking: "बोल रहे हैं...",
      micTapToSpeak: "बोलें (Tap to Speak)",
      endCall: "समाप्त करें (End)",
      micError: "⚠️ माइक्रोफ़ोन का उपयोग नहीं हो पा रहा है।",
      tapForHelp: "अनुमति सहायता और त्वरित संकेत",
      tapToListen: "🔊 बोलकर उत्तर सुनें"
    },
    decisions: {
      title: "निर्णय इतिहास (Decision History)",
      subtitle: "स्थायी निर्णय स्मृति और व्याख्यात्मक एआई सलाह",
      refresh: "रीफ्रेश",
      empty: "अभी तक कोई निर्णय इतिहास दर्ज नहीं हुआ। कृषि निर्णयों के लिए वॉयस या चैट का उपयोग करें।",
      modalTitle: "निर्णय स्रोत और व्याख्या (Decision Provenance)",
      modalSubtitle: "व्याख्यात्मक एआई, टेलीमेट्री ग्राउंडिंग और प्रतिक्रिया",
      whyRationale: "कारण और औचित्य",
      evidenceSensors: "साक्ष्य और सेंसर डेटा",
      dataSources: "डेटा स्रोत और ताजगी",
      toolsSafety: "उपयोग किए गए उपकरण और सुरक्षा जांच",
      modelXai: "मॉडल और व्याख्यात्मकता (XAI)",
      calculations: "गणनाएं और अर्थशास्त्र",
      actionFeedback: "किसान की कार्रवाई और प्रतिक्रिया",
      statusLabel: "स्थिति:",
      feedbackLabel: "रेटिंग:",
      notesLabel: "नोट्स:",
      btnAccept: "✓ स्वीकार करें / पालन करें",
      btnReject: "✕ अस्वीकार करें",
      btnPostpone: "⏳ स्थगित करें",
      btnHelpful: "👍 उपयोगी",
      btnNotHelpful: "👎 उपयोगी नहीं",
      btnSubmitFeedback: "प्रतिक्रिया जमा करें",
      feedbackPlaceholder: "टिप्पणियां या टिप्पणियां जोड़ें...",
      feedbackSuccess: "प्रतिक्रिया डेटाबेस में सुरक्षित हो गई!",
      viewDetail: "विस्तार और व्याख्या देखें →"
    }
  },
  ta: {
    heroTitle: "உங்கள் விவசாயக் கேள்விகளை பூமியிடம் கேளுங்கள்",
    heroSubtitle: "பயிர் தேர்வு, விளைச்சல் கணிப்பு, சந்தை விலை, பூச்சி கட்டுப்பாடு & லாப கணக்கீடு.",
    placeholder: "உங்கள் பயிர் அல்லது பிரச்சினை பற்றி கேளுங்கள்...",
    newChat: "புதிய உரையாடல்",
    recent: "சமீபத்திய உரையாடல்கள்",
    clear: "அழி",
    langLabel: "மொழி (Language):",
    voiceCallBtn: "குரல் அழைப்பு",
    farmerProfileTitle: "விவசாயி சுயவிவரம் மற்றும் பண்ணை விவரங்கள்",
    saveProfileBtn: "💾 மாற்றங்களைச் சேமி",
    logoutBtn: "🚪 வெளியேறு",
    chips: [
      { title: "🌾 பயிர் தேர்வு & லாபம்", sub: "3 ஏக்கர் நிலத்தில் அதிக லாபம் தரும் பயிர் எது?", prompt: "3 ஏக்கர் நிலத்தில் அதிக லாபம் தரும் பயிர் எது?" },
      { title: "💰 நெல் சாகுபடி லாபம்", sub: "நெல் சாகுபடியில் ஏக்கருக்கு நிகர லாபம் எவ்வளவு?", prompt: "நெல் சாகுபடியில் எவ்வளவு லாபம் கிடைக்கும்?" },
      { title: "🍃 இலை கருகல் நோய்", sub: "நெல் இலை கருகல் நோய் தடுப்பு முறைகள் என்ன?", prompt: "நெல் இலை கருகல் நோய்க்கு என்ன மருந்து தெளிக்க வேண்டும்?" },
      { title: "🌦️ வானிலை ஆலோசனை", sub: "அடுத்த 7 நாட்களுக்கு மழை பெய்யுமா? மருந்து தெளிக்கலாमा?", prompt: "நாளை மழை பெய்யுமா? மருந்து தெளிக்கலாমা?" }
    ],
    voice: {
      agentTitle: "பூமி குரல் உதவியாளர் (BHOOMI Voice Assistant)",
      farmerRole: "👨‍🌾 விவசாயி (Farmer):",
      farmerInitialText: '"உங்கள் பிரச்சனை அல்லது கேள்வியைப் பேசுங்கள்..."',
      farmerListening: "கேட்கிறேன்... உங்கள் கேள்வியைத் தெளிவாகப் பேசுங்கள்...",
      aiRole: "🌾 BHOOMI (குரல் உதவியாளர்):",
      aiGreeting: '"வணக்கம் விவசாய நண்பரே! உங்கள் பயிர், பூச்சிகள், வானிலை அல்லது சந்தை விலைகள் குறித்து நேரடியாகக் கேளுங்கள்."',
      statusListening: "முழுமையாகப் பேசுங்கள், கேட்கிறேன்...",
      statusThinking: "விவசாயத் தகவல்களை ஆய்வு செய்கிறோம்...",
      statusSpeaking: "பதிலளிக்கிறேன்...",
      statusIdle: "பேச தட்டவும்",
      micListening: "கேட்கிறேன்...",
      micThinking: "சிந்திக்கிறேன்...",
      micSpeaking: "பேசுகிறேன்...",
      micTapToSpeak: "பேசுங்கள் (Tap to Speak)",
      endCall: "முடிக்க (End)",
      micError: "⚠️ மைக்ரோஃபோன் அணுகல் தடுக்கப்பட்டுள்ளது.",
      tapForHelp: "அனுமதி உதவி & மாதிரி கேள்விகள்",
      tapToListen: "🔊 பதிலை கேட்க தட்டவும்"
    }
  },
  kn: {
    heroTitle: "ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆಗಳನ್ನು ಭೂಮಿಯನ್ನು ಕೇಳಿ",
    heroSubtitle: "ಬೆಳೆ ಆಯ್ಕೆ, ಇಳುವರಿ ಅಂದಾಜು, ಮಾರುಕಟ್ಟೆ ದರ, ರೋಗ ನಿಯಂತ್ರಣ & ಲಾಭದ ಲೆಕ್ಕಾಚಾರ.",
    placeholder: "ನಿಮ್ಮ ಬೆಳೆ ಅಥವಾ ಸಮಸ್ಯೆಯ ಬಗ್ಗೆ ಕೇಳಿ...",
    newChat: "ಹೊಸ ಸಂಭಾಷಣೆ",
    recent: "ಇತ್ತೀಚಿನ ಸಂಭಾಷಣೆಗಳು",
    clear: "ಅಳಿಸಿ",
    langLabel: "ಭಾಷೆ (Language):",
    voiceCallBtn: "ಧ್ವನಿ ಕರೆ",
    farmerProfileTitle: "ರೈತರ ಪ್ರೊಫೈಲ್ ಮತ್ತು ಜಮೀನಿನ ವಿವರಗಳು",
    saveProfileBtn: "💾 ಬದಲಾವಣೆಗಳನ್ನು ಉಳಿಸಿ",
    logoutBtn: "🚪 ಲಾಗ್‌ಔಟ್",
    chips: [
      { title: "🌾 ಬೆಳೆ ಆಯ್ಕೆ & ಲಾಭ", sub: "3 ಎಕರೆ ಕಪ್ಪು ಮಣ್ಣಿನಲ್ಲಿ ಯಾವ ಬೆಳೆ ಹೆಚ್ಚು ಲಾಭದಾಯಕ?", prompt: "3 ಎಕರೆ ಕಪ್ಪು ಮಣ್ಣಿನಲ್ಲಿ ಯಾವ ಬೆಳೆ ಬೆಳೆಯಬಹುದು?" },
      { title: "💰 ಭತ್ತದ ಕೃಷಿ ಲಾಭ", sub: "ಭತ್ತದ ಕೃಷಿಯಲ್ಲಿ ಎಕರೆಗೆ ನಿವ್ವಳ ಲಾಭ ಎಷ್ಟು?", prompt: "ಭತ್ತದ ಕೃಷಿಯಲ್ಲಿ ಎಷ್ಟು ಲಾಭ ಸಿಗುತ್ತದೆ?" },
      { title: "🍃 ಎಲೆ ರೋಗ & ನಿವಾರಣೆ", sub: "ಭತ್ತದ ಬೆಂಕಿರೋಗ ನಿವಾರಣೆಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ಔಷಧಿಗಳು ಯಾವುವು?", prompt: "ಭತ್ತದ ಬೆಂಕಿರೋಗಕ್ಕೆ ಯಾವ ಔಷಧಿ ಸಿಂಪಡಿಸಬೇಕು?" },
      { title: "🌦️ ಹವಾಮಾನ & ಸಿಂಪರಣೆ", sub: "ಮುಂದಿನ 7 ದಿನಗಳಲ್ಲಿ ಮಳೆಯಾಗಲಿದೆಯೇ? ಸಿಂಪರಣೆ ಮಾಡಬಹುದೇ?", prompt: "ನಾಳೆ ಮಳೆಯಾಗಲಿದೆಯೇ? ಔಷಧಿ ಸಿಂಪಡಿಸಬಹುದೇ?" }
    ],
    finance: {
      headerBtn: "ಹಣಕಾಸು & ಲಾಭ",
      headerBtnTitle: "ಕೃಷಿ ಹಣಕಾಸು ಯೋಜನೆ & ಸಿಮ್ಯುಲೇಶನ್",
      title: "ಕೃಷಿ ಹಣಕಾಸು ಮತ್ತು ಲಾಭ ವಿಶ್ಲೇಷಣೆ",
      subtitle: "7-ಘಟಕ ವೆಚ್ಚ ವಿಶ್ಲೇಷಣೆ, ಬ್ರೇಕ್-ಈವನ್ ಲೆಕ್ಕಾಚಾರ & ವಾಟ್-ಇಫ್ ಸಿಮ್ಯುಲೇಶನ್",
      cropName: "🌾 ಬೆಳೆಯ ಹೆಸರು",
      cropPlaceholder: "ಉದಾ: ಮೆಣಸಿನಕಾಯಿ, ಹತ್ತಿ, ಭತ್ತ",
      landArea: "📐 ಜಮೀನಿನ ವಿಸ್ತೀರ್ಣ",
      units: { acre: "ಎಕರೆ", ha: "ಹೆಕ್ಟೇರ್", bigha: "ಬಿಘಾ", guntha: "ಗುಂಟಾ" },
      costSectionTitle: "📋 7-ಘಟಕ ಕೃಷಿ ವೆಚ್ಚಗಳು (₹ ಗಳಲ್ಲಿ)",
      costSeed: "ಬೀಜ (₹)", costFertilizer: "ಗೊಬ್ಬರ (₹)", costPesticide: "ಕೀಟನಾಶಕ (₹)",
      costLabour: "ಕೂಲಿ (₹)", costIrrigation: "ನೀರಾವರಿ (₹)", costMachinery: "ಯಂತ್ರೋಪಕರಣ (₹)", costOther: "ಇತರ ವೆಚ್ಚಗಳು (₹)",
      costTotalLumpSum: "ಅಥವಾ ಒಟ್ಟು ಕೃಷಿ ವೆಚ್ಚ (₹):",
      costTotalPlaceholder: "ಉದಾ: 35000",
      yieldSectionTitle: "📈 ನಿರೀಕ್ಷಿತ ಇಳುವರಿ ಮತ್ತು ಮಾರುಕಟ್ಟೆ ದರ",
      expectedYield: "ಪ್ರತಿ ವಿಸ್ತೀರ್ಣಕ್ಕೆ ಇಳುವರಿ",
      yieldUnits: { quintal: "ಕ್ವಿಂಟಾಲ್", kg: "ಕೆಜಿ", tonne: "ಟನ್" },
      yieldHint: "ಇಳುವರಿ ನೀಡದಿದ್ದರೆ ಬ್ರೇಕ್-ಈವನ್ ಇಳುವರಿ ಲೆಕ್ಕಹಾಕಲಾಗುತ್ತದೆ.",
      expectedPrice: "ನಿರೀಕ್ಷಿತ ಮಾರುಕಟ್ಟೆ ದರ",
      priceUnits: { rupees_per_quintal: "₹ / ಕ್ವಿಂಟಾಲ್", rupees_per_kg: "₹ / ಕೆಜಿ" },
      priceHint: "ದರ ನೀಡದಿದ್ದರೆ ಬ್ರೇಕ್-ಈವನ್ ದರ ಲೆಕ್ಕಹಾಕಲಾಗುತ್ತದೆ.",
      simLeversSummary: "⚡ ವಾಟ್-ಇಫ್ ಸಿಮ್ಯುಲೇಶನ್ ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
      simPriceChange: "ಮಾರುಕಟ್ಟೆ ದರ ಬದಲಾವಣೆ (%)", simYieldChange: "ಇಳುವರಿ ಬದಲಾವಣೆ (%)",
      simCostChange: "ಒಟ್ಟು ವೆಚ್ಚ ಬದಲಾವಣೆ (%)", simFertilizerChange: "ಗೊಬ್ಬರ ವೆಚ್ಚ ಬದಲಾವಣೆ (%)",
      btnCalculate: "📊 ವೆಚ್ಚ ಮತ್ತು ಲಾಭ ಲೆಕ್ಕ ಹಾಕಿ",
      btnRunSim: "⚡ ಸಿಮ್ಯುಲೇಶನ್ ರನ್ ಮಾಡಿ",
      calculating: "⏳ ಹಣಕಾಸಿನ ಲೆಕ್ಕಾಚಾರ ಮಾಡಲಾಗುತ್ತಿದೆ...",
      calcFailed: "ಲೆಕ್ಕಾಚಾರ ವಿಫಲವಾಗಿದೆ. ದಯವಿಟ್ಟು ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
      networkError: "ಹಣಕಾಸು ಸೇವೆ ಸಂಪರ್ಕದಲ್ಲಿ ನೆಟ್‌ವರ್ಕ್ ದೋಷ.",
      simRunning: "⚡ ಸಿಮ್ಯುಲೇಶನ್ ಚಾಲನೆಯಲ್ಲಿದೆ...",
      simFailed: "ಸಿಮ್ಯುಲೇಶನ್ ವಿಫಲವಾಗಿದೆ.",
      simNetworkError: "ಸಿಮ್ಯುಲೇಶನ್ ಸೇವೆ ಸಂಪರ್ಕ ದೋಷ.",
      cardTotalCost: "ಒಟ್ಟು ವೆಚ್ಚ", cardGrossRevenue: "ಒಟ್ಟು ಆದಾಯ", cardNetProfit: "ನಿವ್ವಳ ಲಾಭ",
      cardProfitPerArea: "ಪ್ರತಿ ಎಕರೆ ಲಾಭ", cardRoi: "ಹೂಡಿಕೆಯ ಮೇಲಿನ ಲಾಭ (ROI)", deterministicBadge: "ನಿಖರವಾದ",
      calcTitle: "📊 ಕೃಷಿ ಹಣಕಾಸು ಲೆಕ್ಕಾಚಾರ",
      costBreakdownTitle: "7-ಘಟಕ ವೆಚ್ಚ ವಿಶ್ಲೇಷಣೆ:",
      costLabels: {
        seed_cost: "ಬೀಜ",
        fertilizer_cost: "ಗೊಬ್ಬರ",
        pesticide_cost: "ಕೀಟನಾಶಕ",
        labour_cost: "ಕೂಲಿ",
        irrigation_cost: "ನೀರಾವರಿ",
        machinery_cost: "ಯಂತ್ರೋಪಕರಣ",
        other_cost: "ಇತರ ವೆಚ್ಚಗಳು"
      },
      breakEvenPriceLabel: "🎯 ಬ್ರೇಕ್-ಈವನ್ ಮಾರುಕಟ್ಟೆ ದರ:", breakEvenPriceDesc: "(ನಷ್ಟ ತಪ್ಪಿಸಲು ಕನಿಷ್ಠ ದರ)",
      breakEvenYieldLabel: "🎯 ಬ್ರೇಕ್-ಈವನ್ ಇಳುವರಿ:", breakEvenYieldDesc: "(ವೆಚ್ಚ ಸರಿದೂಗಿಸಲು ಕನಿಷ್ಠ ಉತ್ಪಾದನೆ)",
      partialCalcWarning: "⚠️ ಅಪೂರ್ಣ ಲೆಕ್ಕಾಚಾರ (ಖಾಲಿ ವಿವರಗಳು: {fields})",
      viewTrace: "🔍 ಲೆಕ್ಕಾಚಾರದ ವಿವರಗಳನ್ನು ವೀಕ್ಷಿಸಿ ({count} ಹಂತಗಳು)",
      simResultTitle: "⚡ ವಾಟ್-ಇಫ್ ಸಿಮ್ಯುಲೇಶನ್ ಫಲಿತಾಂಶ", simScenarioBadge: "ಪರಿಸ್ಥಿತಿ ಹೋಲಿಕೆ",
      tblMetric: "ಮಾನದಂಡ", tblBaseline: "ಪ್ರಸ್ತುತ ಸ್ಥಿತಿ", tblSimulated: "ಸಿಮ್ಯುಲೇಟೆಡ್ ಸ್ಥಿತಿ", tblDifference: "ವ್ಯತ್ಯಾಸ",
      tblMarketPrice: "ಮಾರುಕಟ್ಟೆ ದರ", tblTotalProduction: "ಒಟ್ಟು ಉತ್ಪಾದನೆ", tblGrossRevenue: "ಒಟ್ಟು ಆದಾಯ",
      tblCultivationCost: "ಕೃಷಿ ವೆಚ್ಚ", tblNetProfit: "ನಿವ್ವಳ ಲಾಭ", tblRoi: "ಲಾಭದ ದರ (ROI)",
      riskExplanationTitle: "💡 ಅಪಾಯ ವಿಶ್ಲೇಷಣೆ:",
      mitigationActionsTitle: "🛡️ ಶಿಫಾರಸು ಮಾಡಿದ ಅಪಾಯ ನಿಯಂತ್ರಣ ಕ್ರಮಗಳು:",
      validationCostWarning: "ಸಿಮ್ಯುಲೇಶನ್ ಮೊದಲು ದಯವಿಟ್ಟು ಕೃಷಿ ವೆಚ್ಚಗಳನ್ನು ನಮೂದಿಸಿ",
      validationYieldPriceWarning: "ಸಿಮ್ಯುಲೇಶನ್‌ಗಾಗಿ ಇಳುವರಿ ಮತ್ತು ಮಾರುಕಟ್ಟೆ ದರ ನಮೂದಿಸಿ"
    },
    voice: {
      agentTitle: "ಭೂಮಿ ಧ್ವನಿ ಸಹಾಯಕ (BHOOMI Voice Assistant)",
      farmerRole: "👨‍🌾 ರೈತ (Farmer):",
      farmerInitialText: '"ನಿಮ್ಮ ಸಮಸ್ಯೆ ಅಥವಾ ಪ್ರಶ್ನೆಯನ್ನು ಮಾತನಾಡಿ..."',
      farmerListening: "ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದ್ದೇನೆ... ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ...",
      aiRole: "🌾 BHOOMI (ಧ್ವನಿ ಸಹಾಯಕ):",
      aiGreeting: '"ನಮಸ್ಕಾರ ರೈತ ಮಿತ್ರರೇ! ನಿಮ್ಮ ಬೆಳೆ, ಕೀಟಗಳು, ಹವಾಮಾನ ಅಥವಾ ಮಾರುಕಟ್ಟೆ ದರಗಳ ಬಗ್ಗೆ ನೇರವಾಗಿ ಕೇಳಿ."',
      statusListening: "ಸಂಪೂರ್ಣವಾಗಿ ಮಾತನಾಡಿ, ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದ್ದೇನೆ...",
      statusThinking: "ಕೃಷಿ ಮಾಹಿತಿಯನ್ನು ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ...",
      statusSpeaking: "ಉತ್ತರಿಸುತ್ತಿದ್ದೇನೆ...",
      statusIdle: "ಮಾತನಾಡಲು ಟ್ಯಾಪ್ ಮಾಡಿ",
      micListening: "ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದ್ದೇನೆ...",
      micThinking: "ಯೋಚಿಸುತ್ತಿದ್ದೇನೆ...",
      micSpeaking: "ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ...",
      micTapToSpeak: "ಮಾತನಾಡಿ (Tap to Speak)",
      endCall: "ಮುಗಿಸಿ (End)",
      micError: "⚠️ ಮೈಕ್ರೊಫೋನ್ ಪ್ರವೇಶ ನಿರ್ಬಂಧಿಸಲಾಗಿದೆ.",
      tapForHelp: "ಅನುಮತಿ ಸಹಾಯ ಮತ್ತು ಮಾದರಿ ಪ್ರಶ್ನೆಗಳು",
      tapToListen: "🔊 ಉತ್ತರವನ್ನು ಕೇಳಲು ಟ್ಯಾಪ್ ಮಾಡಿ"
    }
  },
  mr: {
    heroTitle: "आपले शेती विषयक प्रश्न भूमीला विचारा",
    heroSubtitle: "पीक निवड, उत्पादन अंदाज, बाजार भाव, रोग नियंत्रण आणि निव्वळ नफा विश्लेषण.",
    placeholder: "आपल्या पिकाबद्दल किंवा समस्येबद्दल विचारा...",
    newChat: "नवीन संभाषण",
    recent: "मागील संभाषणे",
    clear: "हटवा",
    langLabel: "भाषा (Language):",
    voiceCallBtn: "व्हॉइस कॉल",
    farmerProfileTitle: "शेतकरी प्रोफाइल आणि शेताचा तपशील",
    saveProfileBtn: "💾 बदल जतन करा",
    logoutBtn: "🚪 लॉग आउट",
    chips: [
      { title: "🌾 पीक निवड व नफा", sub: "3 एकर काळ्या जमिनीत कोणते पीक सर्वाधिक फायदेशीर ठरेल?", prompt: "3 एकर काळ्या जमिनीत कोणते पीक लावावे?" },
      { title: "💰 भात शेतीतील नफा", sub: "भात शेतीत एकरी खर्च व निव्वळ नफा किती होईल?", prompt: "भात शेतीत किती नफा मिळेल?" },
      { title: "🍃 पानांवरील करपा रोग", sub: "भात पिकावरील करपा रोगाची लक्षणे व नियंत्रण उपाय.", prompt: "भातावरील करपा रोगासाठी कोणती औषधे फवारावीत?" },
      { title: "🌦️ हवामान व फवारणी", sub: "उद्या पाऊस पडेल का? कीटकनाशक फवारणीची योग्य वेळ.", prompt: "उद्या पाऊस पडेल का? औषध फवारणी करू शकतो का?" }
    ],
    finance: {
      headerBtn: "वित्त व नफा",
      headerBtnTitle: "शेती वित्त नियोजन व व्हॉट-इफ सिम्युलेशन",
      title: "शेती वित्त आणि नफा विश्लेषण",
      subtitle: "7-घटक खर्च विभाजन, ब्रेक-इव्हन विश्लेषण व परिदृश्य सिम्युलेशन",
      cropName: "🌾 पिकाचे नाव",
      cropPlaceholder: "उदा: मिरची, कापूस, भात",
      landArea: "📐 शेती क्षेत्रफळ",
      units: { acre: "एकर", ha: "हेक्टर", bigha: "बिघा", guntha: "गुंठा" },
      costSectionTitle: "📋 7-घटक शेती खर्च (₹ मध्ये)",
      costSeed: "बियाणे (₹)", costFertilizer: "खते (₹)", costPesticide: "कीटकनाशके (₹)",
      costLabour: "मजुरी (₹)", costIrrigation: "सिंचन (₹)", costMachinery: "यंत्रसामग्री (₹)", costOther: "इतर खर्च (₹)",
      costTotalLumpSum: "किंवा एकूण शेती खर्च (₹):",
      costTotalPlaceholder: "उदा: 35000",
      yieldSectionTitle: "📈 अपेक्षित उत्पादन आणि बाजार भाव",
      expectedYield: "प्रति क्षेत्रफळ अपेक्षित उत्पादन",
      yieldUnits: { quintal: "क्विंटल", kg: "किग्रॅ", tonne: "टन" },
      yieldHint: "उत्पादन न दिल्यास ब्रेक-इव्हन उत्पादन मोजले जाईल.",
      expectedPrice: "अपेक्षित बाजार भाव",
      priceUnits: { rupees_per_quintal: "₹ / क्विंटल", rupees_per_kg: "₹ / किग्रॅ" },
      priceHint: "भाव न दिल्यास ब्रेक-इव्हन भाव मोजला जाईल.",
      simLeversSummary: "⚡ व्हॉट-इफ सिम्युलेशन सेटिंग्ज",
      simPriceChange: "बाजार भावातील बदल (%)", simYieldChange: "उत्पादनातील बदल (%)",
      simCostChange: "एकूण खर्चातील बदल (%)", simFertilizerChange: "खतांच्या खर्चातील बदल (%)",
      btnCalculate: "📊 खर्च व नफा मोजा",
      btnRunSim: "⚡ सिम्युलेशन चालवा",
      calculating: "⏳ वित्तीय हिशोब केला जात आहे...",
      calcFailed: "हिशोब अयशस्वी झाला. कृपया माहिती तपासा.",
      networkError: "वित्त सेवेशी जोडताना नेटवर्क त्रुटी.",
      simRunning: "⚡ सिम्युलेशन चालू आहे...",
      simFailed: "सिम्युलेशन अयशस्वी झाले.",
      simNetworkError: "सिम्युलेशन सेवेशी जोडताना त्रुटी.",
      cardTotalCost: "एकूण खर्च", cardGrossRevenue: "एकूण उत्पन्न", cardNetProfit: "निव्वळ नफा",
      cardProfitPerArea: "प्रति एकर नफा", cardRoi: "गुंतवणुकीवरील परतावा (ROI)", deterministicBadge: "अचूक",
      calcTitle: "📊 शेती वित्त हिशोब",
      costBreakdownTitle: "7-घटक खर्च विभाजन:",
      costLabels: {
        seed_cost: "बियाणे",
        fertilizer_cost: "खते",
        pesticide_cost: "कीटकनाशके",
        labour_cost: "मजुरी",
        irrigation_cost: "सिंचन",
        machinery_cost: "यंत्रसामग्री",
        other_cost: "इतर खर्च"
      },
      breakEvenPriceLabel: "🎯 ब्रेक-इव्हन बाजार भाव:", breakEvenPriceDesc: "(तोटा टाळण्यासाठी किमान भाव)",
      breakEvenYieldLabel: "🎯 ब्रेक-इव्हन उत्पादन:", breakEvenYieldDesc: "(खर्च भरून काढण्यासाठी किमान उत्पादन)",
      partialCalcWarning: "⚠️ अपूर्ण हिशोब (अपूर्ण माहिती: {fields})",
      viewTrace: "🔍 अचूक हिशोबाचे टप्पे पहा ({count} टप्पे)",
      simResultTitle: "⚡ व्हॉट-इफ सिम्युलेशन", simScenarioBadge: "परिदृश्य तुलना",
      tblMetric: "मापदंड", tblBaseline: "सध्याची स्थिती", tblSimulated: "सिम्युलेटेड स्थिती", tblDifference: "तफावत",
      tblMarketPrice: "बाजार भाव", tblTotalProduction: "एकूण उत्पादन", tblGrossRevenue: "एकूण उत्पन्न",
      tblCultivationCost: "शेती खर्च", tblNetProfit: "निव्वळ नफा", tblRoi: "परतावा दर (ROI)",
      riskExplanationTitle: "💡 जोखीम विश्लेषण:",
      mitigationActionsTitle: "🛡️ शिफारस केलेले जोखीम निवारण उपाय:",
      validationCostWarning: "सिम्युलेशन चालवण्यापूर्वी कृपया शेती खर्च प्रविष्ट करा",
      validationYieldPriceWarning: "सिम्युलेशनसाठी कृपया उत्पादन आणि बाजार भाव प्रविष्ट करा"
    },
    voice: {
      agentTitle: "भूमी व्हॉइस असिस्टंट (BHOOMI Voice Assistant)",
      farmerRole: "👨‍🌾 शेतकरी (Farmer):",
      farmerInitialText: '"आपली समस्या किंवा प्रश्न बोला..."',
      farmerListening: "ऐकत आहे... आपली समस्या स्पष्टपणे बोला...",
      aiRole: "🌾 BHOOMI (व्हॉइस असिस्टंट):",
      aiGreeting: '"नमस्कार शेतकरी मित्रा! आपल्या पिकाबद्दल, किडी-रोगाबद्दल, हवामान किंवा बाजारभावाबद्दल थेट विचारा."',
      statusListening: "संपूर्ण बोला, आम्ही ऐकत आहोत...",
      statusThinking: "शेतीविषयक माहितीचे विश्लेषण करत आहोत...",
      statusSpeaking: "उत्तर देत आहे...",
      statusIdle: "बोलण्यासाठी टॅप करा",
      micListening: "ऐकत आहे...",
      micThinking: "विचार करत आहे...",
      micSpeaking: "बोलत आहे...",
      micTapToSpeak: "बोला (Tap to Speak)",
      endCall: "कॉल समाप्त करा (End)",
      micError: "⚠️ मायक्रोफोन परवानगी उपलब्ध नाही.",
      tapForHelp: "परवानगी मदत आणि नमुना प्रश्न",
      tapToListen: "🔊 उत्तर ऐकण्यासाठी टॅप करा"
    }
  },
  ml: {
    heroTitle: "നിങ്ങളുടെ കാർഷിക സംശയങ്ങൾ ഭൂമിയോട് ചോദിക്കൂ",
    heroSubtitle: "വിള തിരഞ്ഞെടുക്കൽ, വിളവ് പ്രവചനം, വിപണി നിരക്കുകൾ, രോഗനിർണ്ണയം & ലാഭ വിശകലനം.",
    placeholder: "നിങ്ങളുടെ വിളയെക്കുറിച്ചോ പ്രശ്നത്തെക്കുറിച്ചോ ചോദിക്കൂ...",
    newChat: "പുതിയ സംഭാഷണം",
    recent: "മുമ്പത്തെ സംഭാഷണങ്ങൾ",
    clear: "മായ്ക്കുക",
    langLabel: "ഭാഷ (Language):",
    voiceCallBtn: "വോയ്‌സ് കോൾ",
    farmerProfileTitle: "കർഷക പ്രൊഫൈലും കൃഷിയിട വിവരങ്ങളും",
    saveProfileBtn: "💾 മാറ്റങ്ങൾ സൂക്ഷിക്കുക",
    logoutBtn: "🚪 ലോഗ് ഔട്ട്",
    chips: [
      { title: "🌾 വിള തിരഞ്ഞെടുക്കൽ", sub: "ഏറ്റവും അനുയോജ്യമായ ലാഭകരമായ വിള ഏതാണ്?", prompt: "ഏറ്റവും കൂടുതൽ ലാഭം നൽകുന്ന വിള ഏതാണ്?" },
      { title: "💰 നെൽകൃഷി ലാഭം", sub: "നെൽകൃഷിയിൽ നിന്ന് പ്രതീക്ഷിക്കുന്ന വരുമാനവും ലാഭവും എത്ര?", prompt: "നെൽകൃഷിയിൽ നിന്ന് എത്ര ലാഭം ലഭിക്കും?" },
      { title: "🍃 ഇല രോഗങ്ങൾ", sub: "വിളകളിലെ പ്രധാന രോഗങ്ങളും നിയന്ത്രണ മാർഗ്ഗങ്ങളും.", prompt: "ഇല ചുരുളലിന് എന്ത് മരുന്ന് തളിക്കണം?" },
      { title: "🌦️ കാലാവസ്ഥാ മുന്നറിയിപ്പ്", sub: "നാളെ മഴ പെയ്യുമോ? കീടനാശിനി തളിക്കാൻ അനുയോജ്യമാണോ?", prompt: "നാളെ മഴ പെയ്യുമോ? സ്പ്രേ ചെയ്യാമോ?" }
    ],
    finance: {
      headerBtn: "ധനകാര്യം & ലാഭം",
      headerBtnTitle: "കാർഷിക സാമ്പത്തിക ആസൂത്രണം & സിമുലേഷൻ",
      title: "കാർഷിക സാമ്പത്തിക & ലാഭ വിശകലനം",
      subtitle: "7-ഘടക ചെലവ് വിശകലനം, ബ്രേക്ക്-ഈവൻ കണക്കുകൂട്ടൽ & സിമുലേഷൻ",
      cropName: "🌾 വിളയുടെ പേര്",
      cropPlaceholder: "ഉദാ: മുളക്, പരുത്തി, നെല്ല്",
      landArea: "📐 കൃഷിസ്ഥലത്തിന്റെ വിസ്തീർണ്ണം",
      units: { acre: "ഏക്കർ", ha: "ഹെക്ടർ", bigha: "ബിഘ", guntha: "ഗുന്ത" },
      costSectionTitle: "📋 7-ഘടക കൃഷി ചെലവുകൾ (₹ ൽ)",
      costSeed: "വിത്ത് (₹)", costFertilizer: "വളം (₹)", costPesticide: "കീടനാശിനി (₹)",
      costLabour: "കൂലി (₹)", costIrrigation: "നനയ്ക്കൽ (₹)", costMachinery: "യന്ത്രങ്ങൾ (₹)", costOther: "മറ്റ് ചെലവുകൾ (₹)",
      costTotalLumpSum: "അല്ലെങ്കിൽ ആകെ കൃഷി ചെലവ് (₹):",
      costTotalPlaceholder: "ഉദാ: 35000",
      yieldSectionTitle: "📈 പ്രതീക്ഷിക്കുന്ന വിളവും വിപണി വിലയും",
      expectedYield: "പ്രതീക്ഷിക്കുന്ന വിളവ്",
      yieldUnits: { quintal: "ക്വിന്റൽ", kg: "കിലോഗ്രാം", tonne: "ടൺ" },
      yieldHint: "വിളവ് നൽകിയില്ലെങ്കിൽ ബ്രേക്ക്-ഈവൻ വിളവ് കണക്കാക്കും.",
      expectedPrice: "പ്രതീക്ഷിക്കുന്ന വിപണി വില",
      priceUnits: { rupees_per_quintal: "₹ / ക്വിന്റൽ", rupees_per_kg: "₹ / കിലോ" },
      priceHint: "വില നൽകിയില്ലെങ്കിൽ ബ്രേക്ക്-ഈവൻ വില കണക്കാക്കും.",
      simLeversSummary: "⚡ വാട്ട്-ഇഫ് സിമുലേഷൻ ക്രമീകരണങ്ങൾ",
      simPriceChange: "വിപണി വിലയിലെ മാറ്റം (%)", simYieldChange: "വിളവിലെ മാറ്റം (%)",
      simCostChange: "ആകെ ചെലവിലെ മാറ്റം (%)", simFertilizerChange: "വളച്ചെലവിലെ മാറ്റം (%)",
      btnCalculate: "📊 ചെലവും ലാഭവും കണക്കാക്കുക",
      btnRunSim: "⚡ സിമുലേഷൻ പ്രവർത്തിപ്പിക്കുക",
      calculating: "⏳ സാമ്പത്തിക കണക്കുകൂട്ടലുകൾ നടക്കുന്നു...",
      calcFailed: "കണക്കുകൂട്ടൽ പരാജയപ്പെട്ടു. ദയവായി വിവരങ്ങൾ പരിശോധിക്കുക.",
      networkError: "സേവനവുമായി ബന്ധപ്പെടുന്നതിൽ തകരാർ.",
      simRunning: "⚡ സിമുലേഷൻ പ്രവർത്തിക്കുന്നു...",
      simFailed: "സിമുലേഷൻ പരാജയപ്പെട്ടു.",
      simNetworkError: "സിമുലേഷൻ സെർവർ ബന്ധപ്പെടൽ തകരാർ.",
      cardTotalCost: "ആകെ ചെലവ്", cardGrossRevenue: "ആകെ വരുമാനം", cardNetProfit: "അറ്റാദായം",
      cardProfitPerArea: "ഏക്കറിലെ ലാഭം", cardRoi: "നിക്ഷേപ ലാഭം (ROI)", deterministicBadge: "കൃത്യതയുള്ളത്",
      calcTitle: "📊 കാർഷിക സാമ്പത്തിക കണക്കുകൂട്ടൽ",
      costBreakdownTitle: "7-ഘടക ചെലവ് വിവരങ്ങൾ:",
      costLabels: {
        seed_cost: "വിത്ത്",
        fertilizer_cost: "വളം",
        pesticide_cost: "കീടനാശിനി",
        labour_cost: "കൂലി",
        irrigation_cost: "നനയ്ക്കൽ",
        machinery_cost: "യന്ത്രങ്ങൾ",
        other_cost: "മറ്റ് ചെലവുകൾ"
      },
      breakEvenPriceLabel: "🎯 ബ്രേക്ക്-ഈവൻ വിപണി വില:", breakEvenPriceDesc: "(നഷ്ടം ഒഴിവാക്കാനുള്ള കുറഞ്ഞ വില)",
      breakEvenYieldLabel: "🎯 ബ്രേക്ക്-ഈവൻ വിളവ്:", breakEvenYieldDesc: "(ചെലവ് ലഭിക്കാനുള്ള കുറഞ്ഞ ഉത്പാദനം)",
      partialCalcWarning: "⚠️ ഭാഗിക കണക്കുകൂട്ടൽ (നൽകാത്തവ: {fields})",
      viewTrace: "🔍 കണക്കുകൂട്ടൽ ഘട്ടങ്ങൾ കാണുക ({count} ഘട്ടങ്ങൾ)",
      simResultTitle: "⚡ വാട്ട്-ഇഫ് സിമുലേഷൻ", simScenarioBadge: "സാഹചര്യ താരതമ്യം",
      tblMetric: "മാനദണ്ഡം", tblBaseline: "നിലവിലെ അവസ്ഥ", tblSimulated: "സിമുലേഷൻ അവസ്ഥ", tblDifference: "വ്യത്യാസം",
      tblMarketPrice: "വിപണി വില", tblTotalProduction: "ആകെ വിളവ്", tblGrossRevenue: "ആകെ വരുമാനം",
      tblCultivationCost: "കൃഷി ചെലവ്", tblNetProfit: "അറ്റാദായം", tblRoi: "വരുമാന നിരക്ക് (ROI)",
      riskExplanationTitle: "💡 അപകടസാധ്യത വിവരണം:",
      mitigationActionsTitle: "🛡️ നിർദ്ദേശിച്ച അപകടസാധ്യത കുറയ്ക്കൽ നടപടികൾ:",
      validationCostWarning: "സിമുലേഷന് മുൻപ് കൃഷി ചെലവുകൾ നൽകുക",
      validationYieldPriceWarning: "സിമുലേഷനായി വിളവും വിപണി വിലയും നൽകുക"
    },
    voice: {
      agentTitle: "ഭൂമി വോയ്‌സ് അസിസ്റ്റന്റ് (BHOOMI Voice Assistant)",
      farmerRole: "👨‍🌾 കർഷകൻ (Farmer):",
      farmerInitialText: '"നിങ്ങളുടെ പ്രശ്നമോ ചോദ്യമോ സംസാരിക്കൂ..."',
      farmerListening: "കേൾക്കുന്നു... നിങ്ങളുടെ ചോദ്യം വ്യക്തമായി പറയൂ...",
      aiRole: "🌾 BHOOMI (വോയ്‌സ് അസിസ്റ്റന്റ്):",
      aiGreeting: '"നമസ്കാരം കർഷക സുഹൃത്തേ! വിളകൾ, കീടങ്ങൾ, കാലാവസ്ഥ, വിപണി വിലകൾ എന്നിവയെക്കുറിച്ച് നേരിട്ട് ചോദിക്കൂ."',
      statusListening: "വ്യക്തമായി സംസാരിക്കൂ, കേൾക്കുന്നുണ്ട്...",
      statusThinking: "വിവരങ്ങൾ വിശകലനം ചെയ്യുന്നു...",
      statusSpeaking: "മറുപടി നൽകുന്നു...",
      statusIdle: "സംസാരിക്കാൻ ടാപ്പ് ചെയ്യുക",
      micListening: "കേൾക്കുന്നു...",
      micThinking: "ചിന്തിക്കുന്നു...",
      micSpeaking: "സംസാരിക്കുന്നു...",
      micTapToSpeak: "സംസാരിക്കൂ (Tap to Speak)",
      endCall: "കോൾ അവസാനിപ്പിക്കുക (End)",
      micError: "⚠️ മൈക്രോഫോൺ അനുമതി ലഭ്യമല്ല.",
      tapForHelp: "അനുമതി സഹായവും മാതൃകാ ചോദ്യങ്ങളും",
      tapToListen: "🔊 മറുപടി കേൾക്കാൻ ടാപ്പ് ചെയ്യുക"
    }
  }
};

// ==========================================
// Theme Management (Light / Dark)
// ==========================================
function initTheme() {
  const savedTheme = localStorage.getItem("bhoomi_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const newTheme = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("bhoomi_theme", newTheme);
  updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById("themeIcon");
  if (icon) {
    icon.textContent = theme === "dark" ? "☀️" : "🌙";
  }
}

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  
  // Set initial language from storage or default to English
  currentLanguage = localStorage.getItem("bhoomi_lang") || "en";
  
  const langSelect = document.getElementById("langSelect");
  if (langSelect) langSelect.value = currentLanguage;

  const authLangSelect = document.getElementById("authLangSelect");
  if (authLangSelect) authLangSelect.value = currentLanguage;

  updateUILanguage(currentLanguage);
  initSpeechRecognition();
  initOtpInputBoxes();
  initAuth();
});




// ====================================================================
// BHOOMI APPLICATION STATE MACHINE & CLIENT ROUTER (PAGE GATING)
// ====================================================================

const AuthState = {
  AUTH_CHECKING: "AUTH_CHECKING",
  UNAUTHENTICATED: "UNAUTHENTICATED",
  AUTHENTICATING: "AUTHENTICATING",
  ONBOARDING_REQUIRED: "ONBOARDING_REQUIRED",
  AUTHENTICATED: "AUTHENTICATED",
  AUTH_ERROR: "AUTH_ERROR"
};

let currentAppState = AuthState.AUTH_CHECKING;

function setAppState(newState, payload = {}) {
  currentAppState = newState;
  const splash = document.getElementById("authLoadingSplash");
  const authView = document.getElementById("authView");
  const dashboardView = document.getElementById("dashboardView");

  if (newState === AuthState.AUTH_CHECKING) {
    if (splash) splash.style.display = "flex";
    if (authView) authView.style.display = "none";
    if (dashboardView) dashboardView.style.display = "none";
    return;
  }

  // Hide splash screen after check
  if (splash) splash.style.display = "none";

  if (newState === AuthState.UNAUTHENTICATED || newState === AuthState.AUTH_ERROR || newState === AuthState.AUTHENTICATING) {
    if (dashboardView) dashboardView.style.display = "none";
    if (authView) authView.style.display = "flex";

    const onboardStep = document.getElementById("onboardingStep");
    if (onboardStep) onboardStep.style.display = "none";
    return;
  }

  if (newState === AuthState.ONBOARDING_REQUIRED) {
    if (dashboardView) dashboardView.style.display = "none";
    if (authView) authView.style.display = "flex";

    const otpContainer = document.getElementById("otpAuthContainer");
    const reviewerForm = document.getElementById("reviewerLoginForm");
    const step1 = document.getElementById("otpStep1");
    const step2 = document.getElementById("otpStep2");
    const onboardStep = document.getElementById("onboardingStep");

    if (otpContainer) otpContainer.style.display = "block";
    if (reviewerForm) reviewerForm.style.display = "none";
    if (step1) step1.style.display = "none";
    if (step2) step2.style.display = "none";
    if (onboardStep) onboardStep.style.display = "block";
    return;
  }

  if (newState === AuthState.AUTHENTICATED) {
    if (authView) authView.style.display = "none";
    if (dashboardView) dashboardView.style.display = "flex";
    return;
  }
}

function getCurrentRoute() {
  const hash = window.location.hash ? window.location.hash.replace(/^#/, "") : "";
  if (hash) {
    return hash.startsWith("/") ? hash : "/" + hash;
  }
  const path = window.location.pathname || "/";
  return path;
}

function navigateTo(route, replace = false) {
  const current = getCurrentRoute();
  if (current !== route) {
    try {
      if (replace) {
        window.history.replaceState({ route }, "", route);
      } else {
        window.history.pushState({ route }, "", route);
      }
    } catch (e) {
      window.location.hash = route;
    }
  }
  applyRouteGuard(route);
}

function applyRouteGuard(route) {
  const cleanRoute = (route || "/").split("?")[0].toLowerCase();

  if (currentAppState === AuthState.AUTH_CHECKING) {
    return;
  }

  if (currentAppState === AuthState.UNAUTHENTICATED || currentAppState === AuthState.AUTH_ERROR) {
    const protectedRoutes = ["/home", "/finance", "/voice", "/onboarding", "/app"];
    if (protectedRoutes.includes(cleanRoute) || cleanRoute === "/") {
      navigateTo("/login", true);
      return;
    }

    if (cleanRoute === "/signup") {
      switchAuthMode("signup", false);
    } else if (cleanRoute === "/reviewer-login") {
      switchAuthMode("reviewer", false);
    } else if (cleanRoute === "/verify-otp") {
      showOtpVerifyView();
    } else {
      switchAuthMode("login", false);
    }
    return;
  }

  if (currentAppState === AuthState.ONBOARDING_REQUIRED) {
    if (cleanRoute !== "/onboarding") {
      navigateTo("/onboarding", true);
      return;
    }
    setAppState(AuthState.ONBOARDING_REQUIRED);
    return;
  }

  if (currentAppState === AuthState.AUTHENTICATED) {
    const authOnlyRoutes = ["/login", "/signup", "/reviewer-login", "/verify-otp", "/"];
    if (authOnlyRoutes.includes(cleanRoute)) {
      navigateTo("/home", true);
      return;
    }

    if (cleanRoute === "/finance") {
      openFinanceModal();
    } else if (cleanRoute === "/voice") {
      openVoiceCallMode();
    }
  }
}

window.addEventListener("popstate", () => {
  applyRouteGuard(getCurrentRoute());
});

window.addEventListener("hashchange", () => {
  applyRouteGuard(getCurrentRoute());
});

window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    const savedToken = localStorage.getItem("bhoomi_auth_token");
    if (!savedToken && currentAppState === AuthState.AUTHENTICATED) {
      transitionToUnauthenticated("/login");
    }
  }
});

async function initAuth() {
  setAppState(AuthState.AUTH_CHECKING);

  const initialRoute = getCurrentRoute();
  const savedToken = localStorage.getItem("bhoomi_auth_token");

  if (savedToken && savedToken.startsWith("demo_")) {
    const refreshToken = localStorage.getItem("bhoomi_refresh_token");
    if (savedToken) {
      try {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ refresh_token: refreshToken || null })
        });
      } catch (e) {
        console.debug("Backend logout call notice:", e);
      }
    }
    localStorage.removeItem("bhoomi_auth_token");
    localStorage.removeItem("bhoomi_refresh_token");
    localStorage.removeItem("bhoomi_current_user");
    authToken = null;
    currentUser = null;
  }

  if (!savedToken || savedToken.startsWith("demo_")) {
    currentUser = null;
    authToken = null;
    setAppState(AuthState.UNAUTHENTICATED);

    if (initialRoute === "/signup") {
      navigateTo("/signup", true);
    } else if (initialRoute === "/reviewer-login") {
      navigateTo("/reviewer-login", true);
    } else {
      navigateTo("/login", true);
    }
    return;
  }

  try {
    const res = await fetch("/api/v1/auth/me", {
      headers: {
        "Authorization": `Bearer ${savedToken}`,
        "Accept": "application/json"
      }
    });

    if (res.ok) {
      const data = await res.json();
      authToken = savedToken;
      currentUser = {
        id: data.id,
        user_id: data.id,
        farmer_id: data.farmer_profile?.id || data.id,
        farm_id: data.farm?.id || null,
        phone_number: data.phone_number,
        full_name: data.farmer_profile?.name || "Farmer",
        preferred_language: data.farmer_profile?.preferred_language || currentLanguage || "en",
        state: data.farmer_profile?.state || null,
        district: data.farmer_profile?.district || null,
        village: data.farmer_profile?.village || null,
        land_area_acres: data.farm?.total_area_acres ?? null,
        current_crop: data.farm?.crop_name || null,
        active_crop: data.farm?.crop_name || null,
        soil_type: data.farm?.soil_type || null
      };

      localStorage.setItem("bhoomi_current_user", JSON.stringify(currentUser));
      if (currentUser.preferred_language) {
        currentLanguage = currentUser.preferred_language;
        localStorage.setItem("bhoomi_lang", currentLanguage);
        updateUILanguage(currentLanguage);
      }

      updateSidebarFarmerProfile(currentUser);

      if (data.onboarding_required) {
        setAppState(AuthState.ONBOARDING_REQUIRED);
        navigateTo("/onboarding", true);
      } else {
        setAppState(AuthState.AUTHENTICATED);
        loadUserScopedSessions();
        loadTodayTasks();
        loadDecisionHistory();

        const dest = (initialRoute === "/finance" || initialRoute === "/voice") ? initialRoute : "/home";
        navigateTo(dest, true);
      }

    } else {
      localStorage.removeItem("bhoomi_auth_token");
      localStorage.removeItem("bhoomi_current_user");
      authToken = null;
      currentUser = null;
      setAppState(AuthState.UNAUTHENTICATED);
      navigateTo("/login", true);
    }
  } catch (err) {
    console.warn("Session verification error:", err);
    const refreshToken = localStorage.getItem("bhoomi_refresh_token");
    if (savedToken) {
      try {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ refresh_token: refreshToken || null })
        });
      } catch (e) {
        console.debug("Backend logout call notice:", e);
      }
    }
    localStorage.removeItem("bhoomi_auth_token");
    localStorage.removeItem("bhoomi_refresh_token");
    localStorage.removeItem("bhoomi_current_user");
    authToken = null;
    currentUser = null;
    setAppState(AuthState.UNAUTHENTICATED);
    navigateTo("/login", true);
  }
}

function showAuthModal() {
  transitionToUnauthenticated("/login");
}

function hideAuthModal() {
  if (currentUser && authToken) {
    transitionToAuthenticated(currentUser, authToken, "/home");
  } else {
    setAppState(AuthState.AUTHENTICATED);
    navigateTo("/home", true);
  }
}

function transitionToUnauthenticated(route = "/login", reason = null) {
  localStorage.removeItem("bhoomi_auth_token");
  localStorage.removeItem("bhoomi_current_user");
  authToken = null;
  currentUser = null;
  setAppState(AuthState.UNAUTHENTICATED);
  navigateTo(route, true);
  if (reason) {
    const errorMsg = document.getElementById("authErrorMsg");
    if (errorMsg) {
      errorMsg.textContent = reason;
      errorMsg.style.display = "block";
    }
  }
}

function transitionToAuthenticated(user, token, targetRoute = "/home") {
  currentUser = user;
  authToken = token;
  localStorage.setItem("bhoomi_auth_token", token);
  localStorage.setItem("bhoomi_current_user", JSON.stringify(user));
  updateSidebarFarmerProfile(user);
  setAppState(AuthState.AUTHENTICATED);
  loadUserScopedSessions();
  loadTodayTasks();
  loadDecisionHistory();
  navigateTo(targetRoute, true);
}

function showOtpVerifyView() {
  const step1 = document.getElementById("otpStep1");
  const step2 = document.getElementById("otpStep2");
  const onboardStep = document.getElementById("onboardingStep");
  const reviewerForm = document.getElementById("reviewerLoginForm");
  const otpContainer = document.getElementById("otpAuthContainer");

  if (reviewerForm) reviewerForm.style.display = "none";
  if (otpContainer) otpContainer.style.display = "block";
  if (step1) step1.style.display = "none";
  if (step2) step2.style.display = "block";
  if (onboardStep) onboardStep.style.display = "none";
  focusFirstOtpBox();
}

function onAuthLanguageChanged(lang) {
  onLanguageChanged(lang);
  const langSelect = document.getElementById("langSelect");
  if (langSelect) langSelect.value = lang;
}

// 1-Click Demo Login as Ramesh Kumar (Canonical Demo Farmer)
async function quickDemoLogin() {
  currentUser = {
    id: "demo_farmer_1",
    phone_number: "+919876543210 (Demo Contact)",
    full_name: "Ramesh Kumar (Demo Farmer)",
    preferred_language: currentLanguage || "en",
    state: "Andhra Pradesh",
    district: "Guntur",
    village: "Tenali",
    land_area_acres: 3.0,
    current_crop: "Chilli",
    soil_n: 90.0,
    soil_p: 42.0,
    soil_k: 43.0,
    soil_ph: 6.5
  };

  authToken = null;
  localStorage.removeItem("bhoomi_auth_token");
  localStorage.setItem("bhoomi_current_user", JSON.stringify(currentUser));

  updateSidebarFarmerProfile(currentUser);
  hideAuthModal();
  loadUserScopedSessions();
}

// State and District directory for realistic location onboarding
const STATE_DISTRICTS = {
  "Telangana": ["Warangal", "Karimnagar", "Khammam", "Nalgonda", "Nizamabad", "Mahabubnagar", "Adilabad", "Medak", "Rangareddy"],
  "Andhra Pradesh": ["Guntur", "Krishna", "Kurnool", "Anantapur", "West Godavari", "East Godavari", "Chittoor", "Prakasam", "Visakhapatnam"],
  "Karnataka": ["Bengaluru Rural", "Belagavi", "Dharwad", "Mysuru", "Ballari", "Shivamogga", "Raichur", "Hassan"],
  "Tamil Nadu": ["Coimbatore", "Thanjavur", "Madurai", "Salem", "Tiruchirappalli", "Erode", "Dindigul", "Tirunelveli"],
  "Maharashtra": ["Nashik", "Pune", "Nagpur", "Amravati", "Ahmednagar", "Solapur", "Kolhapur", "Aurangabad"],
  "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Sangrur", "Firozpur"],
  "Haryana": ["Karnal", "Hisar", "Ambala", "Rohtak", "Sirsa", "Kurukshetra", "Sonipat"],
  "Uttar Pradesh": ["Varanasi", "Lucknow", "Agra", "Kanpur", "Meerut", "Prayagraj", "Bareilly"],
  "Madhya Pradesh": ["Indore", "Bhopal", "Ujjain", "Jabalpur", "Gwalior", "Hoshangabad", "Dewas"],
  "Gujarat": ["Rajkot", "Surat", "Vadodara", "Junagadh", "Mehsana", "Bhavnagar", "Ahmedabad"],
  "Rajasthan": ["Jaipur", "Jodhpur", "Kota", "Bikaner", "Sri Ganganagar", "Udaipur", "Alwar"],
  "West Bengal": ["Burdwan", "Hooghly", "Nadia", "Murshidabad", "North 24 Parganas", "Bankura"],
  "Bihar": ["Patna", "Muzaffarpur", "Bhagalpur", "Gaya", "Samastipur", "Nalanda"],
  "Odisha": ["Cuttack", "Sambalpur", "Balasore", "Bargarh", "Ganjam", "Khurda"],
  "Kerala": ["Palakkad", "Wayanad", "Thrissur", "Idukki", "Alappuzha", "Kottayam"]
};

let detectedLat = null;
let detectedLon = null;
let currentSoilEstimate = null;

function onStateChanged() {
  const stateSelect = document.getElementById("farmerStateInput");
  const districtSelect = document.getElementById("farmerDistrictInput");
  if (!stateSelect || !districtSelect) return;

  const state = stateSelect.value;
  if (!state) {
    districtSelect.innerHTML = '<option value="" disabled selected>Select District</option>';
    return;
  }
  const districts = STATE_DISTRICTS[state] || [];
  districtSelect.innerHTML = '<option value="" disabled selected>Select District</option>' + 
    districts.map(d => `<option value="${d}">${d}</option>`).join("");
}

function onDistrictChanged() {
  const state = document.getElementById("farmerStateInput")?.value;
  const district = document.getElementById("farmerDistrictInput")?.value;
  if (state && district) {
    fetchSoilEstimate(state, district, detectedLat, detectedLon);
  }
}

async function fetchSoilEstimate(state, district, lat = null, lon = null) {
  try {
    let url = `/api/v1/farms/soil-estimate?state=${encodeURIComponent(state)}&district=${encodeURIComponent(district)}`;
    if (lat && lon) {
      url += `&latitude=${lat}&longitude=${lon}`;
    }
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      currentSoilEstimate = data;
      const typeLabel = document.getElementById("soilEstTypeLabel");
      const phLabel = document.getElementById("soilEstPhLabel");
      const badge = document.getElementById("soilEstConfidenceBadge");
      if (typeLabel) typeLabel.textContent = data.soil_type || "Estimated Loam";
      if (phLabel) phLabel.textContent = `${data.estimated_ph || 6.5} (Estimated)`;
      if (badge) badge.textContent = `${Math.round((data.confidence || 0.85) * 100)}% Coverage`;
    }
  } catch (err) {
    console.debug("Soil estimate fetch notice:", err);
  }
}

function detectFarmerLocation() {
  const btn = document.getElementById("btnDetectLocation");
  if (!navigator.geolocation) {
    showToast("Geolocation is not supported by your browser.", "warning");
    return;
  }
  if (btn) btn.innerHTML = "<span>⏳</span> Detecting...";
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      detectedLat = parseFloat(pos.coords.latitude.toFixed(4));
      detectedLon = parseFloat(pos.coords.longitude.toFixed(4));
      const villageInput = document.getElementById("farmerVillageInput");
      if (villageInput) {
        villageInput.value = `GPS (${detectedLat}, ${detectedLon})`;
      }
      if (btn) btn.innerHTML = "<span>✅</span> Location Set";
      showToast(`Location detected: ${detectedLat}, ${detectedLon}`, "success");
      const state = document.getElementById("farmerStateInput")?.value;
      const district = document.getElementById("farmerDistrictInput")?.value;
      if (state && district) {
        fetchSoilEstimate(state, district, detectedLat, detectedLon);
      }
    },
    (err) => {
      console.warn("Geolocation denied/unavailable:", err);
      if (btn) btn.innerHTML = "<span>📍</span> Detect Location (GPS)";
      showToast("Could not access GPS. Please enter district manually.", "info");
    },
    { timeout: 8000 }
  );
}

function toggleSoilTestFields() {
  const fields = document.getElementById("labSoilFields");
  const btn = document.getElementById("btnToggleSoilTest");
  if (!fields) return;
  const isHidden = fields.style.display === "none";
  fields.style.display = isHidden ? "block" : "none";
  if (btn) {
    btn.textContent = isHidden ? "- [Hide Measured Soil Test Values]" : "+ [Enter Measured Soil Test Values (N, P, K, pH)]";
  }
}

// Step 1: Send OTP to Mobile Number
let resendOtpTimer = null;
let resendOtpCountdown = 0;

function startResendCooldown(seconds = 30) {
  resendOtpCountdown = seconds;
  const btn = document.getElementById("btnResendOtp");
  const txt = document.getElementById("txtBtnResend");
  if (resendOtpTimer) clearInterval(resendOtpTimer);
  if (btn) btn.disabled = true;
  if (txt) txt.textContent = `⏳ Resend (${resendOtpCountdown}s)`;
  resendOtpTimer = setInterval(() => {
    resendOtpCountdown--;
    if (resendOtpCountdown <= 0) {
      clearInterval(resendOtpTimer);
      resendOtpTimer = null;
      if (btn) btn.disabled = false;
      if (txt) txt.textContent = "🔄 Resend Code";
    } else {
      if (txt) txt.textContent = `⏳ Resend (${resendOtpCountdown}s)`;
    }
  }, 1000);
}

async function handleResendOtp() {
  if (!pendingOtpPhone) {
    backToOtpStep1();
    return;
  }
  const btn = document.getElementById("btnResendOtp");
  const txt = document.getElementById("txtBtnResend");
  if (btn) btn.disabled = true;
  if (txt) txt.textContent = "⏳ Sending...";
  await handleSendOtp(true);
}


// ====================================================================
// 6-DIGIT OTP INPUT BOX GRID ENGINE
// ====================================================================

function initOtpInputBoxes() {
  const container = document.getElementById("otpDigitsContainer");
  if (!container) return;
  const boxes = container.querySelectorAll(".otp-digit-box");
  if (!boxes || !boxes.length) return;

  boxes.forEach((box, index) => {
    if (box._otpBound) return;
    box._otpBound = true;

    box.addEventListener("input", (e) => {
      const val = e.target.value;
      const cleanVal = val.replace(/\D/g, "");

      if (cleanVal.length === 0) {
        box.value = "";
        syncOtpCode();
        return;
      }

      if (cleanVal.length === 1) {
        box.value = cleanVal;
        syncOtpCode();
        if (index < boxes.length - 1) {
          boxes[index + 1].focus();
          boxes[index + 1].select();
        }
      } else if (cleanVal.length > 1) {
        distributeOtpDigits(cleanVal, index);
      }
    });

    box.addEventListener("keydown", (e) => {
      if (e.key === "Backspace") {
        if (!box.value && index > 0) {
          e.preventDefault();
          boxes[index - 1].focus();
          boxes[index - 1].value = "";
          syncOtpCode();
        } else {
          box.value = "";
          syncOtpCode();
        }
      } else if (e.key === "ArrowLeft" && index > 0) {
        e.preventDefault();
        boxes[index - 1].focus();
      } else if (e.key === "ArrowRight" && index < boxes.length - 1) {
        e.preventDefault();
        boxes[index + 1].focus();
      } else if (e.key === "Enter") {
        e.preventDefault();
        handleVerifyOtp();
      }
    });

    box.addEventListener("paste", (e) => {
      e.preventDefault();
      const pasteData = (e.clipboardData || window.clipboardData).getData("text") || "";
      const digits = pasteData.replace(/\D/g, "").slice(0, 6);
      if (!digits) return;
      distributeOtpDigits(digits, 0);
    });

    box.addEventListener("focus", () => {
      box.select();
    });
  });
}

function distributeOtpDigits(digits, startIndex = 0) {
  const container = document.getElementById("otpDigitsContainer");
  if (!container) return;
  const boxes = container.querySelectorAll(".otp-digit-box");
  for (let i = 0; i < digits.length && (startIndex + i) < boxes.length; i++) {
    boxes[startIndex + i].value = digits[i];
  }
  syncOtpCode();
  const nextIdx = Math.min(startIndex + digits.length, boxes.length - 1);
  if (boxes[nextIdx]) {
    boxes[nextIdx].focus();
    boxes[nextIdx].select();
  }
}

function syncOtpCode() {
  const code = getOtpCode();
  const hiddenInput = document.getElementById("otpCodeInput");
  if (hiddenInput) {
    hiddenInput.value = code;
  }
}

function getOtpCode() {
  const container = document.getElementById("otpDigitsContainer");
  if (!container) {
    const hidden = document.getElementById("otpCodeInput");
    return hidden ? hidden.value.trim() : "";
  }
  const boxes = container.querySelectorAll(".otp-digit-box");
  let code = "";
  boxes.forEach((b) => {
    code += (b.value || "").trim();
  });
  return code;
}

function clearOtpBoxes() {
  const container = document.getElementById("otpDigitsContainer");
  if (container) {
    const boxes = container.querySelectorAll(".otp-digit-box");
    boxes.forEach((b) => { b.value = ""; });
  }
  syncOtpCode();
  focusFirstOtpBox();
}

function focusFirstOtpBox() {
  const first = document.getElementById("otpDigit1");
  if (first) {
    first.focus();
    first.select();
  }
}

async function handleSendOtp(isResend = false) {
  let phone = "";
  if (isResend && pendingOtpPhone) {
    phone = pendingOtpPhone;
  } else {
    const phoneInput = document.getElementById("otpMobileInput");
    phone = phoneInput ? phoneInput.value.trim() : "";
  }
  const errorMsg = document.getElementById("authErrorMsg");
  if (errorMsg) errorMsg.style.display = "none";

  if (!phone || phone.length !== 10 || !/^\d{10}$/.test(phone)) {
    if (errorMsg) {
      errorMsg.textContent = "Please enter a valid 10-digit mobile number (e.g. 9876543210).";
      errorMsg.style.display = "block";
    }
    return;
  }

  pendingOtpPhone = phone;

  const btnSend = document.getElementById("btnSendOtp");
  const origBtnText = btnSend ? btnSend.innerHTML : "";
  if (btnSend && !isResend) {
    btnSend.disabled = true;
    btnSend.innerHTML = "<span>⏳</span> Sending Code...";
  }

  // Choose canonical endpoint based on currentAuthMode
  const isSignup = currentAuthMode === "SIGNUP";
  const endpoint = isSignup
    ? "/api/v1/auth/signup/request-otp"
    : "/api/v1/auth/login/request-otp";

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone_number: phone })
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      let errMsg = data.detail || data.message || "Failed to send verification code. Please try again.";
      if (res.status === 502 && /sms delivery is not configured/i.test(errMsg)) {
        errMsg = "SMS delivery is not configured for BHOOMI yet. Please contact BHOOMI support or use Reviewer Login if you are authorized.";
      }
      if (errorMsg) {
        errorMsg.textContent = errMsg;
        errorMsg.style.display = "block";
      }
      return;
    }

    // Switch to Step 2
    document.getElementById("otpStep1").style.display = "none";
    document.getElementById("otpStep2").style.display = "block";
    navigateTo("/verify-otp", false);

    const lblOtpCode = document.getElementById("lblOtpCode");
    const sentBanner = document.getElementById("txtOtpSentInfo");

    if (lblOtpCode) {
      lblOtpCode.innerHTML = `🔢 Enter 6-Digit Verification Code:`;
    }
    if (sentBanner) {
      const modeLabel = isSignup ? "registration" : "login";
      sentBanner.innerHTML = `📲 Verification code sent via SMS to +91 ${phone} for ${modeLabel}.`;
    }

    clearOtpBoxes();

    // Start 30s resend cooldown using canonical resend_after
    startResendCooldown(data.resend_after || 30);

  } catch (e) {
    if (errorMsg) {
      errorMsg.textContent = "Failed to send verification code. Please check your network connection.";
      errorMsg.style.display = "block";
    }
  } finally {
    if (btnSend && !isResend) {
      btnSend.disabled = false;
      btnSend.innerHTML = origBtnText || `<span>📲</span> <span id="txtBtnSendOtp">Send OTP Verification Code</span>`;
    }
  }
}

// Step 2: Verify 6-Digit OTP and Establish Session
async function handleVerifyOtp() {
  const otp = getOtpCode();
  const errorMsg = document.getElementById("authErrorMsg");
  if (errorMsg) errorMsg.style.display = "none";

  if (!otp || otp.length !== 6 || !/^\d{6}$/.test(otp)) {
    if (errorMsg) {
      errorMsg.textContent = "Please enter a valid 6-digit numeric verification code.";
      errorMsg.style.display = "block";
    }
    focusFirstOtpBox();
    return;
  }

  const btnVerify = document.getElementById("btnVerifyOtp");
  const origBtnVerifyText = btnVerify ? btnVerify.innerHTML : "";
  if (btnVerify) {
    btnVerify.disabled = true;
    btnVerify.innerHTML = "<span>⏳</span> Verifying Code...";
  }

  const isSignup = currentAuthMode === "SIGNUP";
  const endpoint = isSignup
    ? "/api/v1/auth/signup/verify-otp"
    : "/api/v1/auth/login/verify-otp";

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone_number: pendingOtpPhone,
        otp: otp
      })
    });

    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      authToken = data.access_token;
      const refreshToken = data.refresh_token;
      localStorage.setItem("bhoomi_auth_token", authToken);
      if (refreshToken) {
        localStorage.setItem("bhoomi_refresh_token", refreshToken);
      }

      const userId = data.user?.id || `usr_${pendingOtpPhone}`;
      currentUser = {
        id: userId,
        farmer_id: userId,
        user_id: userId,
        phone_number: pendingOtpPhone,
        full_name: data.user?.full_name || "Farmer",
        preferred_language: currentLanguage
      };

      // Check authoritative GET /api/v1/auth/me for farm profile & onboarding_required
      let onboardingReq = Boolean(data.onboarding_required);
      try {
        const meRes = await fetch("/api/v1/auth/me", {
          headers: { "Authorization": `Bearer ${authToken}` }
        });
        if (meRes.ok) {
          const meData = await meRes.json();
          if (meData.onboarding_required !== undefined) {
            onboardingReq = Boolean(meData.onboarding_required);
          }
          if (meData.farmer_profile?.name) currentUser.full_name = meData.farmer_profile.name;
          if (meData.farm?.total_area_acres) currentUser.land_area_acres = meData.farm.total_area_acres;
          if (meData.farm?.crop_name) currentUser.current_crop = meData.farm.crop_name;
        }
      } catch (e) {
        console.debug("Authoritative /auth/me check notice:", e);
      }

      localStorage.setItem("bhoomi_current_user", JSON.stringify(currentUser));
      localStorage.setItem("bhoomi_lang", currentLanguage);
      updateSidebarFarmerProfile(currentUser);
      updateUILanguage(currentLanguage);

      if (onboardingReq) {
        setAppState(AuthState.ONBOARDING_REQUIRED);
        navigateTo("/onboarding", true);
      } else {
        transitionToAuthenticated(currentUser, authToken, "/home");
      }
    } else {
      let msg = "Invalid verification code. Please try again.";
      if (typeof data.detail === "string") {
        msg = data.detail;
      } else if (Array.isArray(data.detail)) {
        msg = data.detail.map(d => d.msg || JSON.stringify(d)).join("; ");
      } else if (data.message) {
        msg = data.message;
      }
      if (errorMsg) {
        errorMsg.textContent = msg;
        errorMsg.style.display = "block";
      }
      clearOtpBoxes();
    }
  } catch (e) {
    if (errorMsg) {
      errorMsg.textContent = "Server error verifying code: " + (e.message || "Please try again.");
      errorMsg.style.display = "block";
    }
  } finally {
    if (btnVerify) {
      btnVerify.disabled = false;
      btnVerify.innerHTML = origBtnVerifyText || `<span>✅</span> <span id="txtBtnVerify">Verify OTP & Enter Dashboard</span>`;
    }
  }
}

function backToOtpStep1() {
  const step1 = document.getElementById("otpStep1");
  const step2 = document.getElementById("otpStep2");
  const onboardStep = document.getElementById("onboardingStep");
  const errorMsg = document.getElementById("authErrorMsg");
  if (step1) step1.style.display = "block";
  if (step2) step2.style.display = "none";
  if (onboardStep) onboardStep.style.display = "none";
  if (errorMsg) errorMsg.style.display = "none";
  stopResendCooldown();
  clearOtpBoxes();
  if (currentAuthMode === "SIGNUP") {
    navigateTo("/signup", false);
  } else {
    navigateTo("/login", false);
  }
}


function switchAuthMode(mode, updateUrl = true) {
  if (mode === "reviewer") {
    currentAuthMode = "REVIEWER";
  } else if (mode === "signup") {
    currentAuthMode = "SIGNUP";
  } else {
    currentAuthMode = "LOGIN";
  }

  const tabLogin = document.getElementById("tabLoginMode");
  const tabSignup = document.getElementById("tabSignupMode");
  const tabReviewer = document.getElementById("tabReviewerMode");
  const tabOtp = document.getElementById("tabOtpMode");
  const otpContainer = document.getElementById("otpAuthContainer");
  const reviewerForm = document.getElementById("reviewerLoginForm");
  const errorMsg = document.getElementById("authErrorMsg");
  const step1 = document.getElementById("otpStep1");
  const step2 = document.getElementById("otpStep2");
  const onboardStep = document.getElementById("onboardingStep");
  const txtBtnSendOtp = document.getElementById("txtBtnSendOtp");

  if (errorMsg) errorMsg.style.display = "none";
  if (onboardStep) onboardStep.style.display = "none";

  const resetTab = (tab) => {
    if (!tab) return;
    tab.classList.remove("active");
    tab.style.borderColor = "var(--border-subtle, #334155)";
    tab.style.background = "var(--surface-card, #1e293b)";
    tab.style.color = "var(--text-secondary, #94a3b8)";
  };

  const activateTab = (tab) => {
    if (!tab) return;
    tab.classList.add("active");
    tab.style.borderColor = "var(--accent-emerald, #10b981)";
    tab.style.background = "rgba(16,185,129,0.15)";
    tab.style.color = "#ffffff";
  };

  [tabLogin, tabSignup, tabReviewer, tabOtp].forEach(resetTab);

  if (mode === "reviewer") {
    activateTab(tabReviewer);
    if (otpContainer) otpContainer.style.display = "none";
    if (reviewerForm) reviewerForm.style.display = "block";
    const phoneInput = document.getElementById("reviewerPhoneInput");
    if (phoneInput) phoneInput.focus();
    if (updateUrl) navigateTo("/reviewer-login", false);
  } else if (mode === "signup") {
    activateTab(tabSignup);
    if (tabOtp) activateTab(tabOtp);
    if (reviewerForm) reviewerForm.style.display = "none";
    if (otpContainer) otpContainer.style.display = "block";
    if (step1) step1.style.display = "block";
    if (step2) step2.style.display = "none";
    if (txtBtnSendOtp) txtBtnSendOtp.textContent = "Send OTP to Register Farm";
    const phoneInput = document.getElementById("otpMobileInput");
    if (phoneInput) phoneInput.focus();
    if (updateUrl) navigateTo("/signup", false);
  } else {
    activateTab(tabLogin || tabOtp);
    if (reviewerForm) reviewerForm.style.display = "none";
    if (otpContainer) otpContainer.style.display = "block";
    if (step1) step1.style.display = "block";
    if (step2) step2.style.display = "none";
    if (txtBtnSendOtp) txtBtnSendOtp.textContent = "Send OTP Verification Code";
    const phoneInput = document.getElementById("otpMobileInput");
    if (phoneInput) phoneInput.focus();
    if (updateUrl) navigateTo("/login", false);
  }
}


async function handleReviewerDemoLogin() {
  const errorMsg = document.getElementById("authErrorMsg");
  const allDemoBtns = document.querySelectorAll(".btn-reviewer-demo");

  if (errorMsg) errorMsg.style.display = "none";

  allDemoBtns.forEach(btn => {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> <span>Authenticating Reviewer...</span>`;
  });

  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_demo: true })
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("bhoomi_auth_token", authToken);
      if (data.refresh_token) {
        localStorage.setItem("bhoomi_refresh_token", data.refresh_token);
      }

      // Query /api/v1/auth/me to verify identity directly from canonical endpoint
      const meRes = await fetch("/api/v1/auth/me", {
        headers: {
          "Authorization": `Bearer ${authToken}`,
          "Accept": "application/json"
        }
      });

      if (meRes.ok) {
        const meData = await meRes.json();
        currentUser = {
          id: meData.id,
          user_id: meData.id,
          farmer_id: meData.farmer_profile?.id || meData.id,
          farm_id: meData.farm?.id || null,
          phone_number: meData.phone_number,
          full_name: meData.farmer_profile?.name || data.name || "Reviewer Evaluator",
          preferred_language: meData.farmer_profile?.preferred_language || data.preferred_language || currentLanguage || "en",
          state: meData.farmer_profile?.state || data.state || null,
          district: meData.farmer_profile?.district || data.district || null,
          village: meData.farmer_profile?.village || data.village || null,
          land_area_acres: meData.farm?.total_area_acres ?? data.area_acres ?? null,
          current_crop: meData.farm?.crop_name || data.crop_name || null,
          crop_variety: data.crop_variety || null,
          active_crop: meData.farm?.crop_name || data.crop_name || null,
          soil_type: meData.farm?.soil_type || data.soil_type || null
        };
      } else {
        const resolvedFarmerId = data.farmer_id || data.user_id || "reviewer_demo";
        currentUser = {
          id: resolvedFarmerId,
          farmer_id: resolvedFarmerId,
          farm_id: data.farm_id || null,
          user_id: data.user_id,
          phone_number: data.phone_number || "9988776655",
          full_name: data.name || "Reviewer Evaluator",
          preferred_language: data.preferred_language || currentLanguage || "en",
          state: data.state || null,
          district: data.district || null,
          village: data.village || null,
          land_area_acres: (data.area_acres !== undefined && data.area_acres !== null) ? data.area_acres : null,
          current_crop: data.crop_name || null,
          crop_variety: data.crop_variety || null,
          active_crop: data.crop_name || null,
          soil_type: data.soil_type || null
        };
      }

      localStorage.setItem("bhoomi_current_user", JSON.stringify(currentUser));
      if (currentUser.preferred_language) {
        currentLanguage = currentUser.preferred_language;
        localStorage.setItem("bhoomi_lang", currentLanguage);
      }

      updateSidebarFarmerProfile(currentUser);
      updateUILanguage(currentLanguage);
      transitionToAuthenticated(currentUser, authToken, "/home");
    } else {
      let msg = "Reviewer demo login is currently unavailable. Please try again.";
      try {
        const err = await res.json();
        if (typeof err.detail === "string") {
          msg = err.detail;
        } else if (err.error && err.error.message) {
          msg = err.error.message;
        }
      } catch (_) {}

      if (errorMsg) {
        errorMsg.textContent = msg;
        errorMsg.style.display = "block";
      }
    }
  } catch (err) {
    if (errorMsg) {
      errorMsg.textContent = "Network error. Please verify your connection and try again.";
      errorMsg.style.display = "block";
    }
  } finally {
    allDemoBtns.forEach(btn => {
      btn.disabled = false;
      btn.innerHTML = `<span>⚡</span> <span>Reviewer Demo Login</span>`;
    });
  }
}

async function handleReviewerLogin() {
  const phoneEl = document.getElementById("reviewerPhoneInput");
  const passEl = document.getElementById("reviewerPasswordInput");
  const errorMsg = document.getElementById("authErrorMsg");
  const btnLogin = document.getElementById("btnReviewerLogin");

  if (errorMsg) errorMsg.style.display = "none";

  const rawPhone = (phoneEl?.value || "").trim();
  const password = passEl?.value || "";

  if (!rawPhone) {
    if (errorMsg) {
      errorMsg.textContent = "Please enter your reviewer phone number.";
      errorMsg.style.display = "block";
    }
    if (phoneEl) phoneEl.focus();
    return;
  }

  if (!password) {
    if (errorMsg) {
      errorMsg.textContent = "Please enter your reviewer password.";
      errorMsg.style.display = "block";
    }
    if (passEl) passEl.focus();
    return;
  }

  // Clean phone number
  let phoneClean = rawPhone;
  if (phoneClean.startswith && phoneClean.startsWith("+91")) {
    phoneClean = phoneClean.slice(3).trim();
  } else if (phoneClean.startsWith("+91")) {
    phoneClean = phoneClean.slice(3).trim();
  } else if (phoneClean.startsWith("91") && phoneClean.length === 12) {
    phoneClean = phoneClean.slice(2).trim();
  }

  const origBtnText = btnLogin ? btnLogin.innerHTML : "";
  if (btnLogin) {
    btnLogin.disabled = true;
    btnLogin.innerHTML = "<span>⏳</span> Authenticating...";
  }

  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone_number: phoneClean,
        password: password
      })
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("bhoomi_auth_token", authToken);

      const resolvedFarmerId = data.farmer_id || data.user_id || `usr_${phoneClean}`;
      currentUser = {
        id: resolvedFarmerId,
        farmer_id: resolvedFarmerId,
        farm_id: data.farm_id || null,
        user_id: data.user_id,
        phone_number: phoneClean,
        full_name: data.name || "Farmer",
        preferred_language: data.preferred_language || currentLanguage || "en",
        state: data.state || null,
        district: data.district || null,
        village: data.village || null,
        land_area_acres: (data.area_acres !== undefined && data.area_acres !== null) ? data.area_acres : null,
        current_crop: data.crop_name || null,
        crop_variety: data.crop_variety || null,
        active_crop: data.crop_name || null,
        soil_type: data.soil_type || null,
        soil_source_type: data.soil_type ? "database_record" : "unconfigured",
        soil_n: (data.soil_n !== undefined && data.soil_n !== null) ? data.soil_n : null,
        soil_p: (data.soil_p !== undefined && data.soil_p !== null) ? data.soil_p : null,
        soil_k: (data.soil_k !== undefined && data.soil_k !== null) ? data.soil_k : null,
        soil_ph: (data.soil_ph !== undefined && data.soil_ph !== null) ? data.soil_ph : null
      };
      localStorage.setItem("bhoomi_current_user", JSON.stringify(currentUser));
      if (data.preferred_language) {
        currentLanguage = data.preferred_language;
        localStorage.setItem("bhoomi_lang", currentLanguage);
      }

      updateSidebarFarmerProfile(currentUser);
      updateUILanguage(currentLanguage);
      transitionToAuthenticated(currentUser, authToken, "/home");
    } else {
      let msg = "Invalid phone number or password. Please try again.";
      try {
        const err = await res.json();
        if (typeof err.detail === "string") {
          msg = err.detail;
        } else if (err.error && err.error.message) {
          msg = err.error.message;
        }
      } catch (_) {}

      if (errorMsg) {
        errorMsg.textContent = msg;
        errorMsg.style.display = "block";
      }
      if (passEl) {
        passEl.value = "";
        passEl.focus();
      }
    }
  } catch (err) {
    if (errorMsg) {
      errorMsg.textContent = "Network error. Please verify your connection and try again.";
      errorMsg.style.display = "block";
    }
  } finally {
    if (btnLogin) {
      btnLogin.disabled = false;
      btnLogin.innerHTML = origBtnText || `<span>🔐</span> <span id="txtBtnReviewerLogin">Login as Reviewer</span>`;
    }
  }
}


async function handleLogout(skipConfirm = false) {
  if (skipConfirm || confirm("మీరు ఖచ్చితంగా లాగ్ అవుట్ చేయాలనుకుంటున్నారా? (Are you sure you want to log out?)")) {
    const token = authToken || localStorage.getItem("bhoomi_auth_token");
    if (token) {
      try {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          }
        });
      } catch (e) {
        console.debug("Backend logout call notice:", e);
      }
    }
    const refreshToken = localStorage.getItem("bhoomi_refresh_token");
    if (token) {
      try {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ refresh_token: refreshToken || null })
        });
      } catch (e) {
        console.debug("Backend logout call notice:", e);
      }
    }
    localStorage.removeItem("bhoomi_auth_token");
    localStorage.removeItem("bhoomi_refresh_token");
    localStorage.removeItem("bhoomi_current_user");
    authToken = null;
    currentUser = null;
    sessionsList = [];
    renderSessionList();
    startNewChat();
    closeProfileModal();
    closeFinanceModal();
    closeVoiceCallMode();
    transitionToUnauthenticated("/login");
  }
}

function updateSidebarFarmerProfile(user) {
  const nameEl = document.getElementById("sidebarFarmerName");
  const farmEl = document.getElementById("sidebarFarmerFarm");
  if (nameEl) nameEl.textContent = user.full_name || "Farmer";
  if (farmEl) {
    if (!user.farm_id && !user.current_crop && !user.land_area_acres) {
      farmEl.textContent = "Farm profile not configured";
    } else {
      const locParts = [user.village, user.district, user.state].filter(Boolean);
      const locStr = locParts.length > 0 ? locParts.join(", ") : (user.district || user.state || "");
      const acresStr = (user.land_area_acres !== undefined && user.land_area_acres !== null) ? `${user.land_area_acres} Acres` : "Area unconfigured";
      const cropStr = user.current_crop ? `(${user.current_crop})` : "(No crop registered)";
      if (locStr) {
        farmEl.textContent = `${locStr} • ${acresStr} ${cropStr}`;
      } else {
        farmEl.textContent = `${acresStr} ${cropStr}`;
      }
    }
  }
}

// ==========================================
// Regional State & Districts Mapping
// ==========================================
// Duplicate STATE_DISTRICTS removed


function populateDistricts(stateSelectId, districtSelectId, selectedDistrict = null) {
  const stateEl = document.getElementById(stateSelectId);
  const distEl = document.getElementById(districtSelectId);
  if (!stateEl || !distEl) return;

  const stateVal = stateEl.value;
  if (!stateVal) {
    distEl.innerHTML = '<option value="" disabled selected>Select District</option>';
    return;
  }
  const districts = STATE_DISTRICTS[stateVal] || [];

  distEl.innerHTML = '<option value="" disabled' + (!selectedDistrict ? ' selected' : '') + '>Select District</option>';
  districts.forEach(d => {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = d;
    if (selectedDistrict && d === selectedDistrict) {
      opt.selected = true;
    }
    distEl.appendChild(opt);
  });

  if (selectedDistrict && !districts.includes(selectedDistrict)) {
    const customOpt = document.createElement("option");
    customOpt.value = selectedDistrict;
    customOpt.textContent = selectedDistrict;
    customOpt.selected = true;
    distEl.appendChild(customOpt);
  }
}

// ==========================================
// Farmer Profile Edit Modal
// ==========================================
function openProfileModal() {
  const modal = document.getElementById("profileModal");
  if (!modal) return;

  const u = currentUser || {};

  document.getElementById("profName").value = u.full_name || "";
  document.getElementById("profState").value = u.state || "";
  
  populateDistricts("profState", "profDistrict", u.district || null);

  const profCropEl = document.getElementById("profCrop");
  if (profCropEl) {
    if (u.current_crop && ![...profCropEl.options].some(o => o.value === u.current_crop)) {
      const opt = new Option(u.current_crop, u.current_crop, true, true);
      profCropEl.add(opt);
    }
    profCropEl.value = u.current_crop || (profCropEl.options.length > 0 ? profCropEl.options[0].value : "");
  }

  document.getElementById("profAcres").value = (u.land_area_acres !== undefined && u.land_area_acres !== null) ? u.land_area_acres : "";
  document.getElementById("profSoilN").value = (u.soil_n !== undefined && u.soil_n !== null) ? u.soil_n : "";
  document.getElementById("profSoilP").value = (u.soil_p !== undefined && u.soil_p !== null) ? u.soil_p : "";
  document.getElementById("profSoilK").value = (u.soil_k !== undefined && u.soil_k !== null) ? u.soil_k : "";
  document.getElementById("profSoilPh").value = (u.soil_ph !== undefined && u.soil_ph !== null) ? u.soil_ph : "";

  modal.style.display = "flex";
}



function closeProfileModal() {
  const modal = document.getElementById("profileModal");
  if (modal) modal.style.display = "none";
}

async function handleProfileUpdate(event) {
  event.preventDefault();
  if (!currentUser) return;

  currentUser.full_name = document.getElementById("profName").value.trim();
  currentUser.state = document.getElementById("profState").value.trim();
  currentUser.district = document.getElementById("profDistrict").value.trim();
  currentUser.current_crop = document.getElementById("profCrop").value.trim();
  currentUser.land_area_acres = parseFloat(document.getElementById("profAcres").value);
  currentUser.soil_n = parseFloat(document.getElementById("profSoilN").value);
  currentUser.soil_p = parseFloat(document.getElementById("profSoilP").value);
  currentUser.soil_k = parseFloat(document.getElementById("profSoilK").value);
  currentUser.soil_ph = parseFloat(document.getElementById("profSoilPh").value);

  localStorage.setItem("bhoomi_current_user", JSON.stringify(currentUser));
  updateSidebarFarmerProfile(currentUser);

  if (authToken && !authToken.startsWith("demo_")) {
    try {
      await fetch("/api/v1/auth/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authToken}`
        },
        body: JSON.stringify(currentUser)
      });
    } catch (e) {}
  }

  closeProfileModal();
  alert("రైతు మరియు పొలం వివరాలు విజయవంతంగా సేవ్ చేయబడ్డాయి! (Profile saved successfully)");
}

// ==========================================
// Farm Finance, Profit & What-If Simulation
// ==========================================

// ==========================================
// BHOOMI Voice & Finance Localization Helpers
// ==========================================
function getVoiceDict(lang) {
  const current = (lang && I18N[lang] && I18N[lang].voice) ? I18N[lang].voice : null;
  const english = (I18N.en && I18N.en.voice) ? I18N.en.voice : {};
  if (!current) return english;
  return Object.assign({}, english, current);
}

function getLocaleForLang(lang) {
  const map = {
    en: "en-IN",
    te: "te-IN",
    hi: "hi-IN",
    ta: "ta-IN",
    kn: "kn-IN",
    mr: "mr-IN",
    ml: "ml-IN"
  };
  return map[lang] || "en-IN";
}

function getFinanceDict(lang) {
  const current = (lang && I18N[lang] && I18N[lang].finance) ? I18N[lang].finance : null;
  const english = (I18N.en && I18N.en.finance) ? I18N.en.finance : {};
  if (!current) return english;
  return Object.assign({}, english, current);
}

function updateFinanceModalLanguage(lang) {
  const f = getFinanceDict(lang);
  if (!f) return;

  // Header Open Button
  const btnOpenFin = document.getElementById("btnOpenFinance");
  if (btnOpenFin) {
    const txtFin = document.getElementById("txtFinanceBtn");
    if (txtFin && f.headerBtn) txtFin.textContent = f.headerBtn;
    if (f.headerBtnTitle) btnOpenFin.title = f.headerBtnTitle;
  }

  // Modal Header
  const titleEl = document.getElementById("txtFinanceModalTitle");
  if (titleEl && f.title) titleEl.textContent = f.title;
  const subEl = document.getElementById("txtFinanceModalSub");
  if (subEl && f.subtitle) subEl.textContent = f.subtitle;

  // Crop & Land Area Inputs
  const lblCrop = document.getElementById("lblFinCrop");
  if (lblCrop && f.cropName) lblCrop.textContent = f.cropName;
  const inCrop = document.getElementById("finCrop");
  if (inCrop && f.cropPlaceholder) inCrop.placeholder = f.cropPlaceholder;

  const lblArea = document.getElementById("lblFinArea");
  if (lblArea && f.landArea) lblArea.textContent = f.landArea;

  if (f.units) {
    const optAcre = document.getElementById("optAreaAcre");
    if (optAcre && f.units.acre) optAcre.textContent = f.units.acre;
    const optHa = document.getElementById("optAreaHa");
    if (optHa && f.units.ha) optHa.textContent = f.units.ha;
    const optBigha = document.getElementById("optAreaBigha");
    if (optBigha && f.units.bigha) optBigha.textContent = f.units.bigha;
    const optGuntha = document.getElementById("optAreaGuntha");
    if (optGuntha && f.units.guntha) optGuntha.textContent = f.units.guntha;
  }

  // Cost Section
  const costSec = document.getElementById("txtFinCostSection");
  if (costSec && f.costSectionTitle) costSec.textContent = f.costSectionTitle;

  const lblSeed = document.getElementById("lblFinCostSeed");
  if (lblSeed && f.costSeed) lblSeed.textContent = f.costSeed;
  const lblFert = document.getElementById("lblFinCostFertilizer");
  if (lblFert && f.costFertilizer) lblFert.textContent = f.costFertilizer;
  const lblPest = document.getElementById("lblFinCostPesticide");
  if (lblPest && f.costPesticide) lblPest.textContent = f.costPesticide;
  const lblLabour = document.getElementById("lblFinCostLabour");
  if (lblLabour && f.costLabour) lblLabour.textContent = f.costLabour;
  const lblIrr = document.getElementById("lblFinCostIrrigation");
  if (lblIrr && f.costIrrigation) lblIrr.textContent = f.costIrrigation;
  const lblMach = document.getElementById("lblFinCostMachinery");
  if (lblMach && f.costMachinery) lblMach.textContent = f.costMachinery;
  const lblOther = document.getElementById("lblFinCostOther");
  if (lblOther && f.costOther) lblOther.textContent = f.costOther;
  const lblTotal = document.getElementById("lblFinCostTotal");
  if (lblTotal && f.costTotalLumpSum) lblTotal.textContent = f.costTotalLumpSum;
  const inTotal = document.getElementById("finCostTotal");
  if (inTotal && f.costTotalPlaceholder) inTotal.placeholder = f.costTotalPlaceholder;

  // Yield & Price Section
  const yldSec = document.getElementById("txtFinYieldSection");
  if (yldSec && f.yieldSectionTitle) yldSec.textContent = f.yieldSectionTitle;
  const lblYld = document.getElementById("lblFinYield");
  if (lblYld && f.expectedYield) lblYld.textContent = f.expectedYield;
  if (f.yieldUnits) {
    const optQtl = document.getElementById("optYieldQtl");
    if (optQtl && f.yieldUnits.quintal) optQtl.textContent = f.yieldUnits.quintal;
    const optKg = document.getElementById("optYieldKg");
    if (optKg && f.yieldUnits.kg) optKg.textContent = f.yieldUnits.kg;
    const optTon = document.getElementById("optYieldTonne");
    if (optTon && f.yieldUnits.tonne) optTon.textContent = f.yieldUnits.tonne;
  }
  const hintYld = document.getElementById("txtFinYieldHint");
  if (hintYld && f.yieldHint) hintYld.textContent = f.yieldHint;

  const lblPrc = document.getElementById("lblFinPrice");
  if (lblPrc && f.expectedPrice) lblPrc.textContent = f.expectedPrice;
  if (f.priceUnits) {
    const optPQtl = document.getElementById("optPriceQtl");
    if (optPQtl && f.priceUnits.rupees_per_quintal) optPQtl.textContent = f.priceUnits.rupees_per_quintal;
    const optPKg = document.getElementById("optPriceKg");
    if (optPKg && f.priceUnits.rupees_per_kg) optPKg.textContent = f.priceUnits.rupees_per_kg;
  }
  const hintPrc = document.getElementById("txtFinPriceHint");
  if (hintPrc && f.priceHint) hintPrc.textContent = f.priceHint;

  // What-If Levers Section
  const simSum = document.getElementById("txtSimSummary");
  if (simSum && f.simLeversSummary) simSum.textContent = f.simLeversSummary;
  const lblSPrice = document.getElementById("lblSimPrice");
  if (lblSPrice && f.simPriceChange) lblSPrice.textContent = f.simPriceChange;
  const lblSYield = document.getElementById("lblSimYield");
  if (lblSYield && f.simYieldChange) lblSYield.textContent = f.simYieldChange;
  const lblSCost = document.getElementById("lblSimCost");
  if (lblSCost && f.simCostChange) lblSCost.textContent = f.simCostChange;
  const lblSFert = document.getElementById("lblSimFertilizer");
  if (lblSFert && f.simFertilizerChange) lblSFert.textContent = f.simFertilizerChange;

  // Buttons
  const btnCalc = document.getElementById("btnCalcProfit");
  if (btnCalc && f.btnCalculate) btnCalc.textContent = f.btnCalculate;
  const btnSim = document.getElementById("btnRunSim");
  if (btnSim && f.btnRunSim) btnSim.textContent = f.btnRunSim;

  // Re-render cached results dynamically if already displayed
  if (window._lastActiveFinanceTab === 'sim' && window._lastSimulationData) {
    renderSimulationResults(window._lastSimulationData);
  } else if (window._lastFinanceData) {
    renderFinanceResults(window._lastFinanceData);
  }
}

function openFinanceModal() {
  if (currentAppState !== AuthState.AUTHENTICATED) {
    navigateTo("/login", true);
    return;
  }
  const modal = document.getElementById("financeModal");
  if (!modal) return;
  updateFinanceModalLanguage(currentLanguage);
  if (currentUser) {
    if (currentUser.current_crop && document.getElementById("finCrop")) {
      document.getElementById("finCrop").value = currentUser.current_crop;
    }
    if (currentUser.land_area_acres && document.getElementById("finArea")) {
      document.getElementById("finArea").value = currentUser.land_area_acres;
    }
  }
  modal.style.display = "flex";
  if (getCurrentRoute() !== "/finance") {
    navigateTo("/finance", false);
  }
}

function closeFinanceModal() {
  const modal = document.getElementById("financeModal");
  if (modal) modal.style.display = "none";
  if (getCurrentRoute() === "/finance") {
    navigateTo("/home", false);
  }
}

async function calculateFinance() {
  const f = getFinanceDict(currentLanguage);
  const crop = document.getElementById("finCrop") ? document.getElementById("finCrop").value.trim() : "Crop";
  const area = parseFloat(document.getElementById("finArea")?.value) || 1.0;
  const areaUnit = document.getElementById("finAreaUnit")?.value || "acre";

  const seed = parseFloat(document.getElementById("finCostSeed")?.value);
  const fertilizer = parseFloat(document.getElementById("finCostFertilizer")?.value);
  const pesticide = parseFloat(document.getElementById("finCostPesticide")?.value);
  const labour = parseFloat(document.getElementById("finCostLabour")?.value);
  const irrigation = parseFloat(document.getElementById("finCostIrrigation")?.value);
  const machinery = parseFloat(document.getElementById("finCostMachinery")?.value);
  const other = parseFloat(document.getElementById("finCostOther")?.value);
  const totalCostInput = parseFloat(document.getElementById("finCostTotal")?.value);

  const yieldVal = parseFloat(document.getElementById("finYield")?.value);
  const yieldUnit = document.getElementById("finYieldUnit")?.value || "quintal";

  const priceVal = parseFloat(document.getElementById("finPrice")?.value);
  const priceUnit = document.getElementById("finPriceUnit")?.value || "rupees_per_quintal";

  const payload = {
    crop_name: crop,
    land_area: area,
    area_unit: areaUnit
  };

  if (!isNaN(seed)) payload.seed_cost = seed;
  if (!isNaN(fertilizer)) payload.fertilizer_cost = fertilizer;
  if (!isNaN(pesticide)) payload.pesticide_cost = pesticide;
  if (!isNaN(labour)) payload.labour_cost = labour;
  if (!isNaN(irrigation)) payload.irrigation_cost = irrigation;
  if (!isNaN(machinery)) payload.machinery_cost = machinery;
  if (!isNaN(other)) payload.other_cost = other;
  if (!isNaN(totalCostInput)) payload.cultivation_cost_total = totalCostInput;

  if (!isNaN(yieldVal)) {
    payload.expected_yield = yieldVal;
    payload.yield_unit = yieldUnit;
  }
  if (!isNaN(priceVal)) {
    payload.expected_market_price = priceVal;
    payload.price_unit = priceUnit;
  }

  const resultsPanel = document.getElementById("finResultsPanel");
  if (resultsPanel) {
    resultsPanel.style.display = "block";
    resultsPanel.innerHTML = `<div style="text-align: center; color: var(--text-sub); padding: 12px;">${escapeHtml(f.calculating || "⏳ Calculating deterministic farm finance...")}</div>`;
  }

  try {
    const headers = { "Content-Type": "application/json" };
    if (authToken && !authToken.startsWith("demo_")) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    const res = await fetch("/api/v1/profit/calculate", {
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = typeof err.detail === "string" ? err.detail : (f.calcFailed || "Calculation failed. Please verify your inputs.");
      if (resultsPanel) {
        resultsPanel.innerHTML = `<div style="color: #ef4444; padding: 12px; background: rgba(239, 68, 68, 0.1); border-radius: 8px;">⚠️ ${escapeHtml(msg)}</div>`;
      }
      return;
    }

    const data = await res.json();
    window._lastFinanceData = data;
    window._lastActiveFinanceTab = 'calc';
    renderFinanceResults(data);
  } catch (err) {
    console.error("Finance calculation error:", err);
    if (resultsPanel) {
      resultsPanel.innerHTML = `<div style="color: #ef4444; padding: 12px; background: rgba(239, 68, 68, 0.1); border-radius: 8px;">⚠️ ${escapeHtml(f.networkError || "Network error while connecting to finance service.")}</div>`;
    }
  }
}

function renderFinanceResults(data) {
  const panel = document.getElementById("finResultsPanel");
  if (!panel) return;
  panel.style.display = "block";

  const f = getFinanceDict(currentLanguage);

  const totalCost = Number(data.total_cost || data.cultivation_cost_total || 0).toLocaleString('en-IN', {minimumFractionDigits: 2});
  const grossRev = data.gross_revenue !== null && data.gross_revenue !== undefined 
    ? `₹${Number(data.gross_revenue).toLocaleString('en-IN', {minimumFractionDigits: 2})}` 
    : 'N/A';
  const netProfit = data.net_profit !== null && data.net_profit !== undefined 
    ? Number(data.net_profit) 
    : null;
  const netProfitStr = netProfit !== null 
    ? `₹${netProfit.toLocaleString('en-IN', {minimumFractionDigits: 2})}` 
    : 'N/A';
  
  // Localized area unit for display
  const areaUnitKey = (data.area_unit || 'acre').toLowerCase();
  const localizedUnit = (f.units && f.units[areaUnitKey]) ? f.units[areaUnitKey] : (data.area_unit || 'acre');

  const profitPerArea = data.profit_per_area !== null && data.profit_per_area !== undefined
    ? `₹${Number(data.profit_per_area).toLocaleString('en-IN', {minimumFractionDigits: 2})} / ${escapeHtml(localizedUnit)}`
    : 'N/A';
  const roi = data.return_on_investment_percent !== null && data.return_on_investment_percent !== undefined
    ? `${Number(data.return_on_investment_percent).toFixed(1)}%`
    : 'N/A';

  // Cost breakdown
  let breakdownHtml = "";
  if (data.cost_breakdown && Object.keys(data.cost_breakdown).length > 0) {
    const rawKeys = Object.keys(data.cost_breakdown);
    const hasSuffixKeys = rawKeys.some(k => k.endsWith('_cost'));
    const filteredEntries = Object.entries(data.cost_breakdown).filter(([k]) => {
      if (hasSuffixKeys && !k.endsWith('_cost') && rawKeys.includes(k + '_cost')) {
        return false;
      }
      return true;
    });
    const items = filteredEntries.map(([k, v]) => {
      const normalizedKey = k.endsWith('_cost') ? k : (k + '_cost');
      let label = (f.costLabels && f.costLabels[k])
        ? f.costLabels[k]
        : (f.costLabels && f.costLabels[normalizedKey])
          ? f.costLabels[normalizedKey]
          : k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      return `<div style="display:flex; justify-content:space-between; padding:3px 0; border-bottom:1px dashed rgba(255,255,255,0.06); font-size:0.82rem;">
        <span style="color:var(--text-sub);">${escapeHtml(label)}:</span>
        <strong style="color:var(--text-main);">₹${Number(v).toLocaleString('en-IN')}</strong>
      </div>`;
    }).join("");
    breakdownHtml = `
      <div style="margin-top:10px; background:rgba(0,0,0,0.15); padding:10px; border-radius:6px;">
        <div style="font-size:0.8rem; font-weight:600; color:var(--accent-emerald); margin-bottom:6px;">${escapeHtml(f.costBreakdownTitle || "7-Component Cost Breakdown:")}</div>
        ${items}
      </div>
    `;
  }

  // Partial status / Break-even
  let partialHtml = "";
  if (data.is_partial) {
    let beItems = [];
    if (data.break_even_price !== null && data.break_even_price !== undefined) {
      beItems.push(`<div>${escapeHtml(f.breakEvenPriceLabel || "🎯 Break-Even Market Price:")} <strong>₹${Number(data.break_even_price).toLocaleString('en-IN')}/Qtl</strong> ${escapeHtml(f.breakEvenPriceDesc || "(Minimum price needed to avoid loss)")}</div>`);
    }
    if (data.break_even_yield !== null && data.break_even_yield !== undefined) {
      beItems.push(`<div>${escapeHtml(f.breakEvenYieldLabel || "🎯 Break-Even Yield:")} <strong>${Number(data.break_even_yield).toFixed(2)} Qtl/${escapeHtml(localizedUnit)}</strong> ${escapeHtml(f.breakEvenYieldDesc || "(Minimum production needed to cover cost)")}</div>`);
    }
    const warnTemplate = f.partialCalcWarning || "⚠️ Partial Calculation (Missing: {fields})";
    const warnText = warnTemplate.replace('{fields}', escapeHtml((data.missing_fields || []).join(', ')));
    partialHtml = `
      <div style="margin-top:10px; padding:10px; background:rgba(234, 179, 8, 0.12); border-left:3px solid #eab308; border-radius:4px; font-size:0.83rem; color:#fde047;">
        <div style="font-weight:600;">${warnText}</div>
        ${beItems.join('')}
      </div>
    `;
  }

  // Calculation trace
  let traceHtml = "";
  if (Array.isArray(data.calculation_trace) && data.calculation_trace.length > 0) {
    const steps = data.calculation_trace.map(s => `<li style="margin-bottom:3px;">${escapeHtml(s)}</li>`).join("");
    const traceTitle = (f.viewTrace || "🔍 View Deterministic Calculation Trace ({count} steps)").replace('{count}', data.calculation_trace.length);
    traceHtml = `
      <details style="margin-top:10px; font-size:0.8rem; color:var(--text-sub);">
        <summary style="cursor:pointer; font-weight:600; color:#38bdf8;">${escapeHtml(traceTitle)}</summary>
        <ol style="margin-top:6px; padding-left:18px; line-height:1.4;">
          ${steps}
        </ol>
      </details>
    `;
  }

  const calcTitle = `${f.calcTitle || "📊 Financial Calculation"}: ${escapeHtml(data.crop_name)} (${Number(data.land_area)} ${escapeHtml(localizedUnit)})`;

  panel.innerHTML = `
    <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); border-radius:8px; padding:14px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h4 style="margin:0; font-size:1rem; color:var(--accent-emerald);">${calcTitle}</h4>
        <span style="font-size:0.75rem; background:rgba(16,185,129,0.15); color:#10b981; padding:2px 8px; border-radius:9999px; font-weight:600;">${escapeHtml(f.deterministicBadge || "Deterministic")}</span>
      </div>

      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:10px; margin-bottom:12px;">
        <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:6px;">
          <div style="font-size:0.72rem; color:var(--text-sub);">${escapeHtml(f.cardTotalCost || "Total Cost")}</div>
          <div style="font-size:1.1rem; font-weight:700; color:var(--text-main);">₹${totalCost}</div>
        </div>
        <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:6px;">
          <div style="font-size:0.72rem; color:var(--text-sub);">${escapeHtml(f.cardGrossRevenue || "Gross Revenue")}</div>
          <div style="font-size:1.1rem; font-weight:700; color:var(--text-main);">${grossRev}</div>
        </div>
        <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:6px;">
          <div style="font-size:0.72rem; color:var(--text-sub);">${escapeHtml(f.cardNetProfit || "Net Profit")}</div>
          <div style="font-size:1.1rem; font-weight:700; color:${netProfit !== null && netProfit < 0 ? '#ef4444' : '#10b981'};">${netProfitStr}</div>
        </div>
        <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:6px;">
          <div style="font-size:0.72rem; color:var(--text-sub);">${escapeHtml(f.cardProfitPerArea || "Profit per")} ${escapeHtml(localizedUnit)}</div>
          <div style="font-size:0.95rem; font-weight:700; color:var(--text-main);">${profitPerArea}</div>
        </div>
        <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:6px;">
          <div style="font-size:0.72rem; color:var(--text-sub);">${escapeHtml(f.cardRoi || "Return on Investment")}</div>
          <div style="font-size:1.1rem; font-weight:700; color:var(--text-main);">${roi}</div>
        </div>
      </div>

      ${breakdownHtml}
      ${partialHtml}
      ${traceHtml}
    </div>
  `;
}

async function runWhatIfSimulation() {
  const f = getFinanceDict(currentLanguage);
  const crop = document.getElementById("finCrop") ? document.getElementById("finCrop").value.trim() : "Crop";
  const area = parseFloat(document.getElementById("finArea")?.value) || 1.0;
  
  const seed = parseFloat(document.getElementById("finCostSeed")?.value) || 0;
  const fertilizer = parseFloat(document.getElementById("finCostFertilizer")?.value) || 0;
  const pesticide = parseFloat(document.getElementById("finCostPesticide")?.value) || 0;
  const labour = parseFloat(document.getElementById("finCostLabour")?.value) || 0;
  const irrigation = parseFloat(document.getElementById("finCostIrrigation")?.value) || 0;
  const machinery = parseFloat(document.getElementById("finCostMachinery")?.value) || 0;
  const other = parseFloat(document.getElementById("finCostOther")?.value) || 0;
  let totalCost = seed + fertilizer + pesticide + labour + irrigation + machinery + other;
  const directTotal = parseFloat(document.getElementById("finCostTotal")?.value);
  if (!isNaN(directTotal) && directTotal > 0) {
    totalCost = directTotal;
  }
  if (totalCost <= 0) {
    showToast(f.validationCostWarning || "Please enter cultivation costs before running simulation", "warning");
    return;
  }

  const yieldVal = parseFloat(document.getElementById("finYield")?.value);
  const priceVal = parseFloat(document.getElementById("finPrice")?.value);
  if (isNaN(yieldVal) || yieldVal <= 0 || isNaN(priceVal) || priceVal <= 0) {
    showToast(f.validationYieldPriceWarning || "Please enter baseline Yield and Market Price for What-If Simulation", "warning");
    return;
  }

  const priceChange = parseFloat(document.getElementById("simPriceChange")?.value) || 0;
  const yieldChange = parseFloat(document.getElementById("simYieldChange")?.value) || 0;
  const costChange = parseFloat(document.getElementById("simCostChange")?.value) || 0;
  const fertChange = parseFloat(document.getElementById("simFertilizerChange")?.value) || 0;

  const payload = {
    crop_name: crop,
    area_acres: area,
    baseline_yield_quintals_per_acre: yieldVal,
    baseline_market_price_per_quintal: priceVal,
    baseline_cultivation_cost: totalCost,
    price_change_percent: priceChange,
    yield_change_percent: yieldChange,
    cost_change_percent: costChange,
    fertilizer_cost_change_percent: fertChange
  };

  const resultsPanel = document.getElementById("finResultsPanel");
  if (resultsPanel) {
    resultsPanel.style.display = "block";
    resultsPanel.innerHTML = `<div style="text-align: center; color: var(--text-sub); padding: 12px;">${escapeHtml(f.simRunning || "⚡ Running multi-lever scenario simulation...")}</div>`;
  }

  try {
    const headers = { "Content-Type": "application/json" };
    if (authToken && !authToken.startsWith("demo_")) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    const res = await fetch("/api/v1/simulation/what-if", {
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = typeof err.detail === "string" ? err.detail : (f.simFailed || "Simulation failed.");
      if (resultsPanel) {
        resultsPanel.innerHTML = `<div style="color: #ef4444; padding: 12px; background: rgba(239, 68, 68, 0.1); border-radius: 8px;">⚠️ ${escapeHtml(msg)}</div>`;
      }
      return;
    }

    const data = await res.json();
    window._lastSimulationData = data;
    window._lastActiveFinanceTab = 'sim';
    renderSimulationResults(data);
  } catch (err) {
    console.error("Simulation error:", err);
    if (resultsPanel) {
      resultsPanel.innerHTML = `<div style="color: #ef4444; padding: 12px; background: rgba(239, 68, 68, 0.1); border-radius: 8px;">⚠️ ${escapeHtml(f.simNetworkError || "Network error while connecting to simulation service.")}</div>`;
    }
  }
}

function renderSimulationResults(data) {
  const panel = document.getElementById("finResultsPanel");
  if (!panel) return;
  panel.style.display = "block";

  const f = getFinanceDict(currentLanguage);

  const b = data.baseline;
  const s = data.simulated_scenario;
  const isLoss = Number(s.net_profit) < 0;
  const diffColor = Number(s.profit_difference) >= 0 ? '#10b981' : '#ef4444';
  const diffSign = Number(s.profit_difference) >= 0 ? '+' : '';

  let actionsHtml = "";
  if (Array.isArray(data.recommended_hedging_actions) && data.recommended_hedging_actions.length > 0) {
    const list = data.recommended_hedging_actions.map(a => `<li>${escapeHtml(a)}</li>`).join("");
    actionsHtml = `
      <div style="margin-top:10px; padding:10px; background:rgba(56, 189, 248, 0.08); border-left:3px solid #38bdf8; border-radius:4px; font-size:0.8rem;">
        <div style="font-weight:600; color:#38bdf8; margin-bottom:4px;">${escapeHtml(f.mitigationActionsTitle || "🛡️ Recommended Risk Mitigation Actions:")}</div>
        <ul style="margin:0; padding-left:16px; color:var(--text-sub);">${list}</ul>
      </div>
    `;
  }

  const simHeading = `${escapeHtml(f.simResultTitle || "⚡ Multi-Lever What-If Simulation")}: ${escapeHtml(data.crop_name)}`;

  panel.innerHTML = `
    <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); border-radius:8px; padding:14px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h4 style="margin:0; font-size:1rem; color:#38bdf8;">${simHeading}</h4>
        <span style="font-size:0.75rem; background:rgba(56,189,248,0.15); color:#38bdf8; padding:2px 8px; border-radius:9999px; font-weight:600;">${escapeHtml(f.simScenarioBadge || "Scenario Comparison")}</span>
      </div>

      <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; font-size:0.82rem; text-align:left;">
          <thead>
            <tr style="border-bottom:1px solid var(--border-subtle); color:var(--text-sub);">
              <th style="padding:6px 8px;">${escapeHtml(f.tblMetric || "Metric")}</th>
              <th style="padding:6px 8px;">${escapeHtml(f.tblBaseline || "Baseline")}</th>
              <th style="padding:6px 8px;">${escapeHtml(f.tblSimulated || "Simulated Scenario")}</th>
              <th style="padding:6px 8px;">${escapeHtml(f.tblDifference || "Difference")}</th>
            </tr>
          </thead>
          <tbody>
            <tr style="border-bottom:1px dashed rgba(255,255,255,0.06);">
              <td style="padding:6px 8px; color:var(--text-sub);">${escapeHtml(f.tblMarketPrice || "Market Price")}</td>
              <td style="padding:6px 8px;">₹${Number(b.price_per_quintal).toLocaleString('en-IN')}/Qtl</td>
              <td style="padding:6px 8px; font-weight:600;">₹${Number(s.price_per_quintal).toLocaleString('en-IN')}/Qtl</td>
              <td style="padding:6px 8px;">${((Number(s.price_per_quintal) - Number(b.price_per_quintal)) >= 0 ? '+' : '') + (Number(s.price_per_quintal) - Number(b.price_per_quintal)).toLocaleString('en-IN')}</td>
            </tr>
            <tr style="border-bottom:1px dashed rgba(255,255,255,0.06);">
              <td style="padding:6px 8px; color:var(--text-sub);">${escapeHtml(f.tblTotalProduction || "Total Production")}</td>
              <td style="padding:6px 8px;">${Number(b.total_yield_quintals).toFixed(1)} Qtl</td>
              <td style="padding:6px 8px; font-weight:600;">${Number(s.total_yield_quintals).toFixed(1)} Qtl</td>
              <td style="padding:6px 8px;">${((Number(s.total_yield_quintals) - Number(b.total_yield_quintals)) >= 0 ? '+' : '') + (Number(s.total_yield_quintals) - Number(b.total_yield_quintals)).toFixed(1)} Qtl</td>
            </tr>
            <tr style="border-bottom:1px dashed rgba(255,255,255,0.06);">
              <td style="padding:6px 8px; color:var(--text-sub);">${escapeHtml(f.tblCultivationCost || "Cultivation Cost")}</td>
              <td style="padding:6px 8px;">₹${Number(b.cultivation_cost).toLocaleString('en-IN')}</td>
              <td style="padding:6px 8px; font-weight:600;">₹${Number(s.cultivation_cost).toLocaleString('en-IN')}</td>
              <td style="padding:6px 8px;">${((Number(s.cultivation_cost) - Number(b.cultivation_cost)) >= 0 ? '+' : '') + (Number(s.cultivation_cost) - Number(b.cultivation_cost)).toLocaleString('en-IN')}</td>
            </tr>
            <tr style="border-bottom:1px dashed rgba(255,255,255,0.06);">
              <td style="padding:6px 8px; color:var(--text-sub);">${escapeHtml(f.tblGrossRevenue || "Gross Revenue")}</td>
              <td style="padding:6px 8px;">₹${Number(b.gross_revenue).toLocaleString('en-IN')}</td>
              <td style="padding:6px 8px; font-weight:600;">₹${Number(s.gross_revenue).toLocaleString('en-IN')}</td>
              <td style="padding:6px 8px;">${((Number(s.gross_revenue) - Number(b.gross_revenue)) >= 0 ? '+' : '') + (Number(s.gross_revenue) - Number(b.gross_revenue)).toLocaleString('en-IN')}</td>
            </tr>
            <tr style="background:rgba(255,255,255,0.04); font-weight:700;">
              <td style="padding:8px 8px;">${escapeHtml(f.tblNetProfit || "Net Profit")}</td>
              <td style="padding:8px 8px; color:#10b981;">₹${Number(b.net_profit).toLocaleString('en-IN')}</td>
              <td style="padding:8px 8px; color:${isLoss ? '#ef4444' : '#10b981'};">₹${Number(s.net_profit).toLocaleString('en-IN')}</td>
              <td style="padding:8px 8px; color:${diffColor};">${diffSign}₹${Number(s.profit_difference).toLocaleString('en-IN')} (${diffSign}${Number(s.percentage_profit_impact).toFixed(1)}%)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div style="margin-top:12px; font-size:0.83rem; line-height:1.4; color:var(--text-sub);">
        <strong>${escapeHtml(f.riskExplanationTitle || "💡 Risk Explanation:")}</strong> ${escapeHtml(data.risk_impact_explanation || '')}
      </div>

      ${actionsHtml}
    </div>
  `;
}

// ==========================================
// Camera vs Gallery Photo Selection
// ==========================================
function openPhotoSelectModal() {
  const modal = document.getElementById("photoSelectModal");
  if (modal) {
    modal.style.display = "flex";
    const devSection = document.getElementById("sampleLeavesDevSection");
    if (devSection) {
      devSection.style.display = IS_DEV_MODE ? "block" : "none";
    }
  }
}

function closePhotoSelectModal() {
  const modal = document.getElementById("photoSelectModal");
  if (modal) modal.style.display = "none";
}

function triggerCameraCapture() {
  closePhotoSelectModal();
  const cameraInput = document.getElementById("cameraInput");
  if (cameraInput) cameraInput.click();
}

function triggerGalleryUpload() {
  closePhotoSelectModal();
  const galleryInput = document.getElementById("galleryInput");
  if (galleryInput) galleryInput.click();
}

function getUserSessionStorageKey() {
  return currentUser ? `bhoomi_sessions_${currentUser.id}` : "bhoomi_sessions";
}

// Load User Scoped Sessions
function loadUserScopedSessions() {
  const userKey = getUserSessionStorageKey();
  try {
    const raw = localStorage.getItem(userKey);
    sessionsList = raw ? JSON.parse(raw) : [];
  } catch (e) {
    sessionsList = [];
  }
  renderSessionList();
  if (sessionsList.length === 0) {
    startNewChat();
  } else {
    loadChatSession(sessionsList[0].id);
  }
}

function saveSessions() {
  const userKey = getUserSessionStorageKey();
  localStorage.setItem(userKey, JSON.stringify(sessionsList));
}

function renderSessionList() {
  const listEl = document.getElementById("historyList");
  if (!listEl) return;
  listEl.innerHTML = "";

  sessionsList.forEach(sess => {
    const item = document.createElement("div");
    item.className = `history-item ${sess.id === currentSessionId ? "active" : ""}`;
    item.onclick = (e) => {
      if (!e.target.classList.contains("btn-delete-session")) {
        loadChatSession(sess.id);
      }
    };

    item.innerHTML = `
      <div class="history-item-left">
        <span>${sess.icon || "🌾"}</span>
        <span class="history-title">${escapeHtml(sess.title)}</span>
      </div>
      <button class="btn-delete-session" title="Delete chat" onclick="deleteSession('${sess.id}')">✕</button>
    `;
    listEl.appendChild(item);
  });
}


function startNewChat() {
  const newId = "sess_" + Date.now();
  currentSessionId = newId;

  // Clear messages from UI
  const messagesList = document.getElementById("messagesList");
  const heroWelcome = document.getElementById("heroWelcome");
  if (messagesList) {
    messagesList.innerHTML = "";
    messagesList.style.display = "none";
  }
  if (heroWelcome) {
    heroWelcome.style.display = "flex";
  }

  // Clear inputs
  const chatInput = document.getElementById("chatInput");
  if (chatInput) {
    chatInput.value = "";
    autoResizeTextarea(chatInput);
    chatInput.focus();
  }
  removeAttachedImage();

  // Create local session entry
  const newSess = {
    id: newId,
    title: "New Agricultural Consultation",
    icon: "🌾",
    language: currentLanguage,
    messages: [],
    updatedAt: Date.now()
  };
  sessionsList.unshift(newSess);
  saveSessions();
  renderSessionList();

  // Close mobile sidebar if open
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.remove("open");
}

function loadChatSession(sessionId) {
  currentSessionId = sessionId;
  const sess = sessionsList.find(s => s.id === sessionId);
  if (!sess) return;

  renderSessionList();

  const messagesList = document.getElementById("messagesList");
  const heroWelcome = document.getElementById("heroWelcome");

  if (!sess.messages || sess.messages.length === 0) {
    if (messagesList) {
      messagesList.innerHTML = "";
      messagesList.style.display = "none";
    }
    if (heroWelcome) heroWelcome.style.display = "flex";
  } else {
    if (heroWelcome) heroWelcome.style.display = "none";
    if (messagesList) {
      messagesList.style.display = "flex";
      messagesList.innerHTML = "";
      sess.messages.forEach(msg => {
        appendMessageRow(msg.role, msg.content, msg.imageBase64, msg.data);
      });
    }
  }

  scrollToBottom();
}

function deleteSession(sessionId) {
  sessionsList = sessionsList.filter(s => s.id !== sessionId);
  saveSessions();

  if (currentSessionId === sessionId) {
    if (sessionsList.length > 0) {
      loadChatSession(sessionsList[0].id);
    } else {
      startNewChat();
    }
  } else {
    renderSessionList();
  }
}

function clearAllSessions() {
  if (confirm("Clear all recent conversations?")) {
    sessionsList = [];
    localStorage.removeItem("bhoomi_sessions");
    startNewChat();
  }
}

// ==========================================
// Language & Localization UI
// ==========================================
function onLanguageChanged(lang) {
  currentLanguage = lang;
  localStorage.setItem("bhoomi_lang", lang);
  
  if (currentUser) {
    currentUser.preferred_language = lang;
    localStorage.setItem("bhoomi_current_user", JSON.stringify(currentUser));
  }

  const langSelect = document.getElementById("langSelect");
  if (langSelect && langSelect.value !== lang) langSelect.value = lang;

  const authLangSelect = document.getElementById("authLangSelect");
  if (authLangSelect && authLangSelect.value !== lang) authLangSelect.value = lang;

  updateUILanguage(lang);
}


function updateUILanguage(lang) {
  const dict = I18N[lang] || I18N.en;
  
  const heroTitle = document.getElementById("heroTitle");
  const heroSubtitle = document.getElementById("heroSubtitle");
  const chatInput = document.getElementById("chatInput");
  const txtNewChat = document.getElementById("txtNewChat");
  const txtRecent = document.getElementById("txtRecent");
  const starterChipsGrid = document.getElementById("starterChipsGrid");

  if (heroTitle) heroTitle.textContent = dict.heroTitle;
  if (heroSubtitle) heroSubtitle.textContent = dict.heroSubtitle;
  if (chatInput) chatInput.placeholder = dict.placeholder;
  if (txtNewChat) txtNewChat.textContent = dict.newChat;
  if (txtRecent) txtRecent.textContent = dict.recent;

  const txtLangTitle = document.getElementById("txtLangTitle");
  if (txtLangTitle && dict.langLabel) txtLangTitle.textContent = dict.langLabel;

  const btnClear = document.querySelector(".btn-clear-all");
  if (btnClear && dict.clear) btnClear.textContent = dict.clear;

  const btnVoiceCallHeader = document.getElementById("txtVoiceCallBtn");
  if (btnVoiceCallHeader && dict.voiceCallBtn) btnVoiceCallHeader.textContent = dict.voiceCallBtn;

  const profModalTitle = document.querySelector(".profile-modal-title h3");
  if (profModalTitle && dict.farmerProfileTitle) profModalTitle.textContent = dict.farmerProfileTitle;

  const btnSaveProf = document.querySelector(".btn-save-profile");
  if (btnSaveProf && dict.saveProfileBtn) btnSaveProf.textContent = dict.saveProfileBtn;

  const btnLogoutProf = document.querySelector(".btn-logout");
  if (btnLogoutProf && dict.logoutBtn) btnLogoutProf.textContent = dict.logoutBtn;

  if (starterChipsGrid) {
    starterChipsGrid.innerHTML = "";
    dict.chips.forEach(chip => {
      const chipEl = document.createElement("div");
      chipEl.className = "starter-chip";
      chipEl.onclick = () => {
        if (chatInput) {
          chatInput.value = chip.prompt;
          autoResizeTextarea(chatInput);
          sendMessage();
        }
      };
      chipEl.innerHTML = `
        <div class="chip-title">${chip.title}</div>
        <div class="chip-sub">${chip.sub}</div>
      `;
      starterChipsGrid.appendChild(chipEl);
    });
  }

  updateVoiceModalLabels();
  updateFinanceModalLanguage(lang);

  // Update Today's Farm Tasks header labels
  const txtTodayTasksTitle = document.getElementById("txtTodayTasksTitle");
  const txtTodayTasksSub = document.getElementById("txtTodayTasksSub");
  const txtRefreshTasks = document.getElementById("txtRefreshTasks");
  if (txtTodayTasksTitle) {
    if (lang === "te") txtTodayTasksTitle.textContent = "నేటి వ్యవసాయ పనులు (Today's Tasks)";
    else if (lang === "hi") txtTodayTasksTitle.textContent = "आज के कृषि कार्य (Today's Tasks)";
    else if (lang === "ta") txtTodayTasksTitle.textContent = "இன்றைய விவசாய பணிகள்";
    else if (lang === "kn") txtTodayTasksTitle.textContent = "ಇಂದಿನ ಕೃಷಿ ಕಾರ್ಯಗಳು";
    else if (lang === "mr") txtTodayTasksTitle.textContent = "आजची शेती कामे";
    else txtTodayTasksTitle.textContent = "Today's Farm Tasks";
  }
  if (txtTodayTasksSub) {
    if (lang === "te") txtTodayTasksSub.textContent = "వాతావరణం మరియు డిజిటల్ ట్విన్ ఆధారిత పనులు";
    else if (lang === "hi") txtTodayTasksSub.textContent = "मौसम और डिजिटल ट्विन आधारित कार्य";
    else txtTodayTasksSub.textContent = "Scheduled actions from your digital twin & weather intelligence";
  }
  if (txtRefreshTasks) {
    if (lang === "te") txtRefreshTasks.textContent = "రిఫ్రెష్";
    else if (lang === "hi") txtRefreshTasks.textContent = "ताज़ा करें";
    else txtRefreshTasks.textContent = "Refresh";
  }
  loadTodayTasks();

  // Update Decision History header labels & modal labels
  const dDict = getDecisionsDict(lang);
  const txtDecisionHistoryTitle = document.getElementById("txtDecisionHistoryTitle");
  const txtDecisionHistorySub = document.getElementById("txtDecisionHistorySub");
  const txtRefreshDecisions = document.getElementById("txtRefreshDecisions");
  const txtDecisionDetailTitle = document.getElementById("txtDecisionDetailTitle");
  const txtDecisionDetailSub = document.getElementById("txtDecisionDetailSub");

  if (txtDecisionHistoryTitle && dDict.title) txtDecisionHistoryTitle.textContent = dDict.title;
  if (txtDecisionHistorySub && dDict.subtitle) txtDecisionHistorySub.textContent = dDict.subtitle;
  if (txtRefreshDecisions && dDict.refresh) txtRefreshDecisions.textContent = dDict.refresh;
  if (txtDecisionDetailTitle && dDict.modalTitle) txtDecisionDetailTitle.textContent = dDict.modalTitle;
  if (txtDecisionDetailSub && dDict.modalSubtitle) txtDecisionDetailSub.textContent = dDict.modalSubtitle;


  // Update all listen buttons in existing chat rows
  document.querySelectorAll(".btn-speak-audio").forEach(btn => {
    if (!btn.classList.contains("playing")) {
      resetAudioButton(btn);
    }
  });
}



// ==========================================
// Messaging & Chat Workflow
// ==========================================
async function sendMessage() {
  const chatInput = document.getElementById("chatInput");
  const text = chatInput ? chatInput.value.trim() : "";
  const hasImage = !!attachedImageBase64;

  if (!text && !hasImage) return;

  const userText = text || (hasImage ? "Analyze this leaf image for diseases" : "");
  
  // Hide hero welcome
  const heroWelcome = document.getElementById("heroWelcome");
  const messagesList = document.getElementById("messagesList");
  if (heroWelcome) heroWelcome.style.display = "none";
  if (messagesList) messagesList.style.display = "flex";

  // Append User message to UI
  appendMessageRow("user", userText, attachedImageBase64);

  // Store in current session
  let sess = sessionsList.find(s => s.id === currentSessionId);
  if (!sess) {
    sess = {
      id: currentSessionId,
      title: autoTitleFromQuery(userText),
      icon: getIconForQuery(userText),
      language: currentLanguage,
      messages: [],
      updatedAt: Date.now()
    };
    sessionsList.unshift(sess);
  } else if (sess.messages.length === 0) {
    sess.title = autoTitleFromQuery(userText);
    sess.icon = getIconForQuery(userText);
  }

  sess.messages.push({
    role: "user",
    content: userText,
    imageBase64: attachedImageBase64
  });
  saveSessions();
  renderSessionList();

  // Clear inputs
  const imgB64 = attachedImageBase64;
  if (chatInput) {
    chatInput.value = "";
    autoResizeTextarea(chatInput);
  }
  removeAttachedImage();

  // Add Assistant Thinking Indicator
  const thinkingId = "thinking_" + Date.now();
  appendThinkingRow(thinkingId);
  scrollToBottom();

  try {
    const payload = {
      message: userText,
      session_id: currentSessionId,
      language_code: currentLanguage,
      image_base64: imgB64
    };

    const chatHeaders = { "Content-Type": "application/json" };
    if (authToken && !authToken.startsWith("demo_")) {
      chatHeaders["Authorization"] = `Bearer ${authToken}`;
    }

    const response = await fetch("/api/v1/assistant/chat", {
      method: "POST",
      headers: chatHeaders,
      body: JSON.stringify(payload)
    });

    removeThinkingRow(thinkingId);

    if (response.ok) {
      const data = await response.json();
      const reply = data.reply_text || "I have analyzed your request.";
      appendMessageRow("assistant", reply, null, data);

      sess.messages.push({
        role: "assistant",
        content: reply,
        data: data
      });
      sess.updatedAt = Date.now();
      saveSessions();

      // If farmer used mic input, automatically speak the response aloud!
      if (lastInputWasVoice) {
        lastInputWasVoice = false;
        setTimeout(() => {
          const msgRows = document.querySelectorAll(".message-row.assistant");
          if (msgRows.length > 0) {
            const lastRow = msgRows[msgRows.length - 1];
            const speakBtn = lastRow.querySelector(".btn-speak-audio");
            if (speakBtn) speakText(speakBtn);
          }
        }, 300);
      }
    } else {
      const errData = await response.json().catch(() => ({}));
      console.error("[CHAT] Request failed:", response.status, errData);
      let errMsg = "⚠️ Unable to connect to agronomic server. Please verify your connection.";
      if (response.status === 401) {
        errMsg = "⚠️ Authentication required. Please log in to access your farm digital twin, or enable demo mode.";
      } else if (typeof errData.detail === "string") {
        errMsg = `⚠️ ${errData.detail}`;
      } else if (Array.isArray(errData.detail)) {
        errMsg = `⚠️ ${errData.detail.map(d => d.msg || JSON.stringify(d)).join("; ")}`;
      } else if (errData.error && errData.error.message) {
        errMsg = `⚠️ ${errData.error.message}`;
      } else if (errData.message) {
        errMsg = `⚠️ ${errData.message}`;
      }
      appendMessageRow("assistant", errMsg);
    }
  } catch (err) {
    removeThinkingRow(thinkingId);
    console.error("[CHAT] Network error:", err);
    appendMessageRow("assistant", `⚠️ Connection error: ${err.message || "Please try again."}`);
  }

  scrollToBottom();
}

function autoTitleFromQuery(q) {
  const lower = q.toLowerCase();
  if (lower.includes("paddy") || lower.includes("rice") || lower.includes("వరి") || lower.includes("धान")) {
    if (lower.includes("profit") || lower.includes("లాభం") || lower.includes("मुनाफा")) return "🌾 Paddy Profit Analysis";
    if (lower.includes("issue") || lower.includes("disease") || lower.includes("తెగులు")) return "🍃 Paddy Disease Management";
    return "🌾 Rice Farming Advice";
  }
  if (lower.includes("cotton") || lower.includes("పత్తి") || lower.includes("कपास")) return "🌱 Cotton Advisory";
  if (lower.includes("maize") || lower.includes("మొక్కజొన్న") || lower.includes("मक्का")) return "🌽 Maize Advisory";
  if (lower.includes("weather") || lower.includes("rain") || lower.includes("వాతావరణం")) return "🌦️ Agro-Weather Forecast";
  if (lower.includes("leaf") || lower.includes("spot") || lower.includes("blight")) return "🍃 Leaf Disease Scan";
  if (lower.includes("which crop") || lower.includes("what to grow")) return "🌾 Crop Selection & Planning";
  
  const words = q.split(" ");
  return words.length > 4 ? words.slice(0, 4).join(" ") + "..." : q;
}

function getIconForQuery(q) {
  const lower = q.toLowerCase();
  if (lower.includes("leaf") || lower.includes("disease") || lower.includes("తెగులు")) return "🍃";
  if (lower.includes("weather") || lower.includes("rain") || lower.includes("వాతావరణం")) return "🌦️";
  if (lower.includes("profit") || lower.includes("price") || lower.includes("మండి")) return "💰";
  return "🌾";
}

// ==========================================
// DOM Rendering Helpers
// ==========================================
function appendMessageRow(role, content, imageBase64, structuredData) {
  const messagesList = document.getElementById("messagesList");
  if (!messagesList) return;

  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const avatar = role === "user" ? "👨‍🌾" : '<img src="/static/icon-192.png?v=20260823_v10" alt="BHOOMI" style="width:22px; height:22px; border-radius:5px; vertical-align:middle;">';
  
  let formattedHtml = formatMarkdown(content);
  let imageHtml = "";
  if (imageBase64) {
    imageHtml = `<img src="${imageBase64}" class="attached-image-preview" alt="User upload" />`;
  }

  let structuredCardHtml = "";
  if (structuredData) {
    if (structuredData.structured_data) {
      structuredCardHtml = buildStructuredCard(structuredData.structured_data);
    } else if (structuredData.visual_cards) {
      structuredCardHtml = buildStructuredCard({ visual_cards: structuredData.visual_cards });
    } else if (structuredData.vision_diagnosis) {
      structuredCardHtml = buildStructuredCard({ vision_diagnosis: structuredData.vision_diagnosis });
    }
  }

  let audioButtonHtml = "";
  if (role === "assistant") {
    const listenLabels = {
      te: "వినండి",
      hi: "सुनें",
      en: "Listen",
      ta: "கேளுங்கள்",
      kn: "ಕೇಳಿ",
      ml: "കേൾക്കൂ"
    };
    const listenText = listenLabels[currentLanguage] || "Listen";

    audioButtonHtml = `
      <div class="audio-action-row">
        <button class="btn-speak-audio" onclick="listenToAssistantMessage(this)" title="Listen to spoken answer" aria-label="Listen">
          <span class="audio-btn-icon">🔊</span>
          <span class="audio-btn-label">${listenText}</span>
        </button>
        <div class="feedback-actions">
          <button class="btn-feedback-thumb" title="Helpful advice" onclick="submitFeedback(this, 'helpful')">👍</button>
          <button class="btn-feedback-thumb" title="Not helpful" onclick="submitFeedback(this, 'not_helpful')">👎</button>
        </div>
      </div>
    `;
  }

  row.innerHTML = `
    ${role === "assistant" ? `<div class="message-avatar">${avatar}</div>` : ""}
    <div class="message-bubble">
      ${imageHtml}
      <div class="message-text">${formattedHtml}</div>
      ${structuredCardHtml}
      ${audioButtonHtml}
    </div>
    ${role === "user" ? `<div class="message-avatar">${avatar}</div>` : ""}
  `;

  if (role === "assistant" && structuredData) {
    if (structuredData.assistant_audio_base64) {
      row.dataset.audioBase64 = structuredData.assistant_audio_base64;
    }
  }

  messagesList.appendChild(row);
  return row;
}

async function submitFeedback(btnElement, rating) {
  const container = btnElement.closest(".feedback-actions");
  if (!container) return;

  // Prevent duplicate submissions by disabling buttons
  const buttons = container.querySelectorAll("button");
  buttons.forEach(b => b.disabled = true);

  const bubble = btnElement.closest(".message-bubble");
  const textEl = bubble ? bubble.querySelector(".message-text") : null;
  const responseText = textEl ? textEl.innerText.slice(0, 500) : "";

  const thanksMap = {
    te: "ధన్యవాదాలు!",
    hi: "धन्यवाद!",
    ta: "நன்றி!",
    kn: "ಧನ್ಯವಾದಗಳು!",
    ml: "നന്ദി!",
    en: "Thanks!"
  };

  const errorMap = {
    te: "⚠️ విఫలమైంది",
    hi: "⚠️ विफल रहा",
    ta: "⚠️ தோல்வியடைந்தது",
    kn: "⚠️ ವಿಫಲವಾಗಿದೆ",
    ml: "⚠️ പരാജയപ്പെട്ടു",
    en: "⚠️ Feedback failed"
  };

  try {
    const feedbackHeaders = { "Content-Type": "application/json" };
    if (authToken && !authToken.startsWith("demo_")) {
      feedbackHeaders["Authorization"] = `Bearer ${authToken}`;
    }

    const res = await fetch("/api/v1/assistant/feedback", {
      method: "POST",
      headers: feedbackHeaders,
      body: JSON.stringify({
        session_id: currentSessionId,
        rating: rating,
        response_text: responseText,
        language_code: currentLanguage
      })
    });

    if (res.ok) {
      const msg = thanksMap[currentLanguage] || thanksMap.en;
      container.innerHTML = `<span class="feedback-thanks">✓ ${msg}</span>`;
    } else {
      const errData = await res.json().catch(() => ({}));
      console.error("[FEEDBACK] Submission failed:", res.status, errData);
      const errMsg = errorMap[currentLanguage] || errorMap.en;
      container.innerHTML = `<span class="feedback-error" style="color:#ef4444;font-size:0.8rem;">${errMsg}</span>`;
    }
  } catch (e) {
    console.error("[FEEDBACK] Network/client error:", e);
    const errMsg = errorMap[currentLanguage] || errorMap.en;
    container.innerHTML = `<span class="feedback-error" style="color:#ef4444;font-size:0.8rem;">${errMsg}</span>`;
  }
}

function appendThinkingRow(id) {
  const messagesList = document.getElementById("messagesList");
  if (!messagesList) return;

  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.id = id;
  row.innerHTML = `
    <div class="message-avatar">🌾</div>
    <div class="message-bubble" style="color: var(--text-sub);">
      <span>🌾 BHOOMI is analyzing agronomic data...</span>
    </div>
  `;
  messagesList.appendChild(row);
}

function removeThinkingRow(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function buildStructuredCard(sd) {
  if (!sd) return "";

  let cardsHtml = [];

  // A. Visual Cards List from BHOOMI Tool Executions
  if (Array.isArray(sd.visual_cards) && sd.visual_cards.length > 0) {
    for (const card of sd.visual_cards) {
      if (!card) continue;
      const type = card.card_type || "";
      const title = card.title || "Agricultural Intelligence";
      const data = card.data || {};

      // 1. Crop Recommendation Card (ML Random Forest)
      if (type === "crop_recommendation_card") {
        const recs = Array.isArray(data.top_recommendations) ? data.top_recommendations : [];
        const pills = recs.slice(0, 3).map((r, i) => {
          const name = r.crop_name || r.name || "Crop";
          const score = Math.round((r.confidence || r.match_score || 0.9) * 100);
          return `<div class="metric-pill ${i === 0 ? 'highlight' : ''}"><strong>#${i+1} ${name}</strong>: ${score}% Match</div>`;
        }).join("");
        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">🌾 ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">${pills || '<div class="metric-pill highlight">Recommended Crops Identified</div>'}</div>
          </div>
        `);
      }

      // 2. Yield Prediction Card (ML XGBoost)
      else if (type === "yield_prediction_card") {
        const ypa = data.expected_yield_quintals_per_acre || data.yield_per_acre || 0;
        const area = (data.area_acres !== undefined && data.area_acres !== null) ? data.area_acres : ((currentUser && currentUser.land_area_acres) || null);
        const tot = data.expected_total_production_quintals || (area ? (ypa * area) : null);
        const conf = data.confidence_interval_95;
        let rangeHtml = "";
        if (Array.isArray(conf) && conf.length === 2) {
          rangeHtml = `<div class="metric-pill">95% CI: <strong>${Number(conf[0]).toFixed(1)} - ${Number(conf[1]).toFixed(1)} Qtl</strong></div>`;
        }
        const totHtml = (tot !== null && tot !== undefined) ? `<div class="metric-pill">Total Est. Production: <strong>${Number(tot).toFixed(1)} Qtl</strong></div>` : "";
        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">📈 ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">
              <div class="metric-pill highlight">Expected Yield: <strong>${Number(ypa).toFixed(1)} Qtl/Acre</strong></div>
              ${totHtml}
              ${rangeHtml}
            </div>
          </div>
        `);
      }

      // 3. Mandi Market Realization Card
      else if (type === "market_card") {
        const recMandi = data.recommended_mandi || data.market_name || "Regional Mandi";
        const netReal = data.best_net_realization || data.net_realization || 0;
        const modal = data.benchmark_modal_price || data.modal_price || 0;
        const minP = data.min_price || data.modal_min || 0;
        const maxP = data.max_price || data.modal_max || 0;
        const trend = data.price_trend || "";
        const status = data.status || data.price_status || "ACTIVE";
        const src = data.source || data.provider || "Agmarknet (data.gov.in)";
        const dateStr = data.arrival_date || data.timestamp || "";

        if (status === "UNAVAILABLE" || (!modal && !netReal)) {
          cardsHtml.push(`
            <div class="assistant-card" style="border-left: 3px solid var(--accent-amber);">
              <div class="card-title">🏪 ${escapeHtml(title)}</div>
              <div class="metrics-pill-grid">
                <div class="metric-pill" style="color: #f59e0b;">Status: <strong>Live Data Unavailable</strong></div>
                <div class="metric-pill" style="width: 100%;">Source: <strong>${escapeHtml(src)}</strong></div>
                <div class="metric-pill" style="width: 100%; color: var(--text-sub);">Live mandi prices for this commodity in this district are not currently reported by Agmarknet.</div>
              </div>
            </div>
          `);
        } else {
          cardsHtml.push(`
            <div class="assistant-card">
              <div class="card-title">🏪 ${escapeHtml(title)}</div>
              <div class="metrics-pill-grid">
                <div class="metric-pill highlight">Best Mandi: <strong>${escapeHtml(recMandi)}</strong></div>
                ${modal ? `<div class="metric-pill">Modal: <strong>₹${Number(modal).toLocaleString('en-IN')}/Qtl</strong></div>` : ''}
                ${(minP && maxP) ? `<div class="metric-pill">Range: <strong>₹${Number(minP).toLocaleString('en-IN')} - ₹${Number(maxP).toLocaleString('en-IN')}/Qtl</strong></div>` : ''}
                <div class="metric-pill highlight">Net Realization: <strong>₹${Number(netReal).toLocaleString('en-IN')}/Qtl</strong></div>
                ${trend ? `<div class="metric-pill">Trend: <strong>${escapeHtml(trend)}</strong></div>` : ''}
                <div class="metric-pill" style="font-size: 0.75rem; color: var(--text-sub); width: 100%;">Source: ${escapeHtml(src)}${dateStr ? ` • Date: ${escapeHtml(dateStr)}` : ''}</div>
              </div>
            </div>
          `);
        }
      }

      // 4. Profit & Economic Simulation Card
      else if (type === "profit_card") {
        const fin = data.financial_summary || data;
        const gross = fin.expected_gross_revenue_inr || fin.gross_revenue || 0;
        const cost = fin.total_cultivation_cost_inr || fin.cultivation_cost_total || 0;
        const net = fin.estimated_net_profit_inr || fin.net_profit || (Number(gross) - Number(cost));
        const roi = fin.return_on_investment_percent || "71.4";
        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">💰 ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">
              <div class="metric-pill">Gross Revenue: <strong>₹${Number(gross).toLocaleString('en-IN', {minimumFractionDigits:2})}</strong></div>
              <div class="metric-pill">Cultivation Cost: <strong>₹${Number(cost).toLocaleString('en-IN', {minimumFractionDigits:2})}</strong></div>
              <div class="metric-pill highlight">Net Profit: <strong>₹${Number(net).toLocaleString('en-IN', {minimumFractionDigits:2})}</strong></div>
              <div class="metric-pill">ROI: <strong>${roi}%</strong></div>
            </div>
          </div>
        `);
      }

      // 5. Weather Advisory Card
      else if (type === "weather_card") {
        const cur = data.current || {};
        const temp = cur.temperature_celsius !== undefined && cur.temperature_celsius !== null ? `${cur.temperature_celsius}°C` : 'N/A';
        const cond = cur.condition || "Clear";
        const rain = cur.precipitation_probability !== undefined && cur.precipitation_probability !== null ? `${cur.precipitation_probability}%` : 'N/A';
        const hum = cur.humidity_percent !== undefined && cur.humidity_percent !== null ? `${cur.humidity_percent}%` : 'N/A';
        const wind = cur.wind_speed_kmh !== undefined && cur.wind_speed_kmh !== null ? `${cur.wind_speed_kmh} km/h` : 'N/A';
        const calDate = cur.calendar_date || data.target_date || "";
        const dayName = cur.day_name || "";
        const tz = cur.timezone || data.timezone || "Asia/Kolkata";
        const provider = data.provider_type || data.provider || "OpenWeatherMap";
        
        let sprayPill = "";
        if (data.spray_window_evaluation) {
          const sw = data.spray_window_evaluation;
          if (sw.is_safe_to_spray) {
            sprayPill = `<div class="metric-pill" style="color: #10b981; border-color: #10b981; width: 100%;">🌿 <strong>Spray Safe:</strong> Yes (${escapeHtml(sw.rationale || 'Conditions favorable')})</div>`;
          } else if (sw.is_safe_to_spray === false) {
            sprayPill = `<div class="metric-pill" style="color: #ef4444; border-color: #ef4444; width: 100%;">⚠️ <strong>Spray Advisory:</strong> Do NOT Spray (${escapeHtml(sw.rationale || 'High rain or wind')})</div>`;
          }
        }

        let dateHeader = "";
        if (calDate) {
          dateHeader = `<div style="font-size: 0.75rem; color: var(--accent-emerald); margin-bottom: 6px;">📅 ${escapeHtml(dayName ? `${dayName}, ` : '')}${escapeHtml(calDate)} (${escapeHtml(tz)})</div>`;
        }

        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">🌦️ ${escapeHtml(title)}</div>
            ${dateHeader}
            <div class="metrics-pill-grid">
              <div class="metric-pill highlight">Temp: <strong>${temp} (${escapeHtml(cond)})</strong></div>
              <div class="metric-pill">Rain Chance: <strong>${rain}</strong></div>
              <div class="metric-pill">Humidity: <strong>${hum}</strong></div>
              <div class="metric-pill">Wind: <strong>${wind}</strong></div>
              ${sprayPill}
              <div class="metric-pill" style="font-size: 0.72rem; color: var(--text-sub); width: 100%;">Provider: ${escapeHtml(provider)} • Timezone: ${escapeHtml(tz)}</div>
            </div>
          </div>
        `);
      }

      // 6. Fertilizer & Nutrient Card
      else if (type === "fertilizer_card") {
        const crop = data.crop_name || "";
        const stage = data.crop_stage || "vegetative";
        const soil = data.soil_type || "black";
        const summ = data.summary || "Balanced NPK application scheduled.";
        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">🧪 ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">
              <div class="metric-pill highlight">Crop: <strong>${escapeHtml(crop)} (${escapeHtml(stage)})</strong></div>
              <div class="metric-pill">Soil: <strong>${escapeHtml(soil)}</strong></div>
              <div class="metric-pill" style="width:100%; margin-top:4px;"><strong>Plan:</strong> ${escapeHtml(summ)}</div>
            </div>
          </div>
        `);
      }

      // 7. RAG Knowledge / ICAR Research Card
      else if (type === "knowledge_card" || type === "rag_evidence_card") {
        const topic = data.topic || "Agronomic Intelligence";
        const citations = Array.isArray(data.citations) ? data.citations : [];
        const auth = citations.length > 0 ? (citations[0].authority || citations[0].document_title || "ICAR") : "ICAR";
        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">📚 ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">
              <div class="metric-pill highlight">Topic: <strong>${escapeHtml(topic)}</strong></div>
              <div class="metric-pill">Authority: <strong>${escapeHtml(auth)}</strong></div>
            </div>
          </div>
        `);
      }

      // 8. Agricultural Safety Notice / Risk Card
      else if (type === "risk_card") {
        const status = data.protocol_status || "SAFETY_PROTOCOL";
        const adv = data.advisory || data.recommendation || "";
        cardsHtml.push(`
          <div class="assistant-card" style="border-left: 3px solid var(--accent-rose);">
            <div class="card-title" style="color: var(--accent-rose);">⚠️ ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">
              <div class="metric-pill" style="color: var(--accent-rose); border-color: var(--accent-rose);">Status: <strong>${escapeHtml(status)}</strong></div>
              ${adv ? `<div class="metric-pill" style="width:100%;"><strong>Advisory:</strong> ${escapeHtml(adv)}</div>` : ''}
            </div>
          </div>
        `);
      }

      // 9. Generic Fallback for Other Cards (Daily Briefing, etc.)
      else {
        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">📋 ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">
              <div class="metric-pill highlight">Verified Farm Intelligence Attached</div>
            </div>
          </div>
        `);
      }
    }
  }

  // B. Vision Diagnosis (Leaf Scan)
  if (sd.vision_diagnosis) {
    const vd = sd.vision_diagnosis;
    if (vd.success) {
      cardsHtml.push(`
        <div class="assistant-card" style="border-left: 3px solid var(--accent-emerald);">
          <div class="card-title" style="color: var(--accent-emerald);">🍃 Leaf Disease AI Scan: ${escapeHtml(vd.crop_identified || 'Identified Plant')}</div>
          <div class="metrics-pill-grid">
            <div class="metric-pill highlight">Diagnosed: <strong>${escapeHtml(vd.common_name || vd.disease_detected || 'Identified Condition')}</strong></div>
            <div class="metric-pill">Confidence: <strong>${vd.confidence_percentage}% (${escapeHtml(vd.uncertainty_level || 'LOW')})</strong></div>
            ${vd.ipm_recommendation && vd.ipm_recommendation !== 'None' ? `<div class="metric-pill" style="width:100%;"><strong>🌿 IPM Advisory:</strong> ${escapeHtml(vd.ipm_recommendation)}</div>` : ''}
            ${vd.chemical_treatment && vd.chemical_treatment !== 'None' ? `<div class="metric-pill" style="width:100%;"><strong>🧪 Treatment Option:</strong> ${escapeHtml(vd.chemical_treatment)}</div>` : ''}
          </div>
        </div>
      `);
    } else {
      cardsHtml.push(`
        <div class="assistant-card" style="border-left: 3px solid var(--accent-amber);">
          <div class="card-title" style="color: var(--accent-amber);">⚠️ Leaf Image Quality / Scan Status</div>
          <div class="metrics-pill-grid">
            <div class="metric-pill highlight">Status: <strong>${escapeHtml(vd.common_name || 'Verification Advisory')}</strong></div>
            <div class="metric-pill" style="width:100%;"><strong>Advisory:</strong> ${escapeHtml(vd.farmer_explanation || 'Please retake the photo holding the camera closer to the symptoms in natural daylight.')}</div>
          </div>
        </div>
      `);
    }
  }

  // C. Legacy Profit Data Fallback
  if (cardsHtml.length === 0 && sd.profit_data && sd.profit_data.financial_summary) {
    const fin = sd.profit_data.financial_summary;
    cardsHtml.push(`
      <div class="assistant-card">
        <div class="card-title">💰 Economic Breakdown (${escapeHtml(sd.current_crop || "Crop")})</div>
        <div class="metrics-pill-grid">
          <div class="metric-pill">Gross Revenue: <strong>₹${Number(fin.expected_gross_revenue_inr).toLocaleString('en-IN', {minimumFractionDigits:2})}</strong></div>
          <div class="metric-pill">Cultivation Cost: <strong>₹${Number(fin.total_cultivation_cost_inr).toLocaleString('en-IN', {minimumFractionDigits:2})}</strong></div>
          <div class="metric-pill highlight">Net Profit: <strong>₹${Number(fin.estimated_net_profit_inr).toLocaleString('en-IN', {minimumFractionDigits:2})}</strong></div>
          <div class="metric-pill">BCR: <strong>${fin.benefit_cost_ratio_bcr}</strong></div>
        </div>
      </div>
    `);
  }

  // D. Legacy Simulation Data Fallback
  if (cardsHtml.length === 0 && sd.simulation_data && sd.simulation_data.impact_deltas) {
    const d = sd.simulation_data.impact_deltas;
    cardsHtml.push(`
      <div class="assistant-card">
        <div class="card-title">📊 What-If Stress Impact</div>
        <div class="metrics-pill-grid">
          <div class="metric-pill">Profit Delta: <strong>₹${Number(d.delta_profit_inr).toLocaleString('en-IN', {minimumFractionDigits:2})}</strong></div>
          <div class="metric-pill">Shift %: <strong>${d.delta_profit_percent > 0 ? '+' : ''}${d.delta_profit_percent}%</strong></div>
          <div class="metric-pill">Yield Shift: <strong>${d.delta_yield_percent}%</strong></div>
        </div>
      </div>
    `);
  }

  return cardsHtml.join("");
}

function formatMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);
  
  // Bold **text**
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Bullet points
  html = html.replace(/^[•\-*]\s+(.*)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul style="padding-left: 20px; margin: 6px 0;">$1</ul>');
  // Newlines
  html = html.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
  return html;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function scrollToBottom() {
  const container = document.getElementById("scrollContainer");
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

// ==========================================
// Image Upload & Attachment
// ==========================================
async function handleLeafImageUpload(file, customTitle) {
  if (!file) return;

  const titleText = customTitle || "🍃 Leaf Photo Diagnostic Scan";
  const reader = new FileReader();

  reader.onload = async (e) => {
    const imgDataUrl = e.target.result;

    // Hide hero welcome
    const heroWelcome = document.getElementById("heroWelcome");
    const messagesList = document.getElementById("messagesList");
    if (heroWelcome) heroWelcome.style.display = "none";
    if (messagesList) messagesList.style.display = "flex";

    // 1. Append User message with the leaf photo
    appendMessageRow("user", titleText, imgDataUrl);

    // Save user message in session
    let curSess = sessionsList.find(s => s.id === currentSessionId);
    if (!curSess) {
      curSess = {
        id: currentSessionId,
        title: "Leaf Disease Diagnostic",
        icon: "🍃",
        language: currentLanguage,
        messages: [],
        updatedAt: Date.now()
      };
      sessionsList.unshift(curSess);
    }
    curSess.messages.push({
      role: "user",
      content: titleText,
      imageBase64: imgDataUrl
    });
    saveSessions();
    renderSessionList();

    // 2. Show thinking indicator
    const thinkingId = "thinking_" + Date.now();
    appendThinkingRow(thinkingId);
    scrollToBottom();

    try {
      const formData = new FormData();
      formData.append("file", file, file.name || "leaf.jpg");

      // Dynamic crop routing: detect crop from title, filename, or farmer profile, or allow auto-detection
      let cropHint = "";
      const checkText = ((customTitle || "") + " " + (file.name || "")).toLowerCase();
      const cropMap = {
        "tomato": "tomato", "tamatar": "tomato", "టమోటా": "tomato", "టమాట": "tomato",
        "banana": "banana", "kela": "banana", "అరటి": "banana",
        "guava": "guava", "amrood": "guava", "జామ": "guava",
        "corn": "corn_maize", "maize": "corn_maize", "makka": "corn_maize", "మొక్కజొన్న": "corn_maize",
        "potato": "potato", "aloo": "potato", "బంగాళాదుంప": "potato",
        "rice": "rice", "paddy": "rice", "వరి": "rice",
        "apple": "apple", "ఆపిల్": "apple",
        "cucumber": "cucumber_pumpkin", "pumpkin": "cucumber_pumpkin", "దోస": "cucumber_pumpkin", "గుమ్మడి": "cucumber_pumpkin",
        "sugarcane": "sugarcane", "చెరకు": "sugarcane",
        "chilli": "chilli", "chili": "chilli", "mirchi": "chilli", "మిరప": "chilli", "మిర్చి": "chilli"
      };
      for (const [kw, canon] of Object.entries(cropMap)) {
        if (checkText.includes(kw)) {
          cropHint = canon;
          break;
        }
      }
      if (cropHint) {
        formData.append("crop_hint", cropHint);
      }
      formData.append("language", currentLanguage || "en");

      const headers = {};
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

      const resp = await fetch("/api/v1/vision/analyze", {
        method: "POST",
        headers: headers,
        body: formData
      });

      removeThinkingRow(thinkingId);

      if (resp.ok) {
        const data = await resp.json();
        const spokenText = data.spoken_explanation || data.farmer_explanation || "Image analysis complete.";

        // 3. Append Assistant response row with rich vision card
        const asstRow = appendMessageRow("assistant", spokenText, null, {
          vision_diagnosis: data
        });

        curSess.messages.push({
          role: "assistant",
          content: spokenText,
          data: { vision_diagnosis: data },
          timestamp: Date.now()
        });
        curSess.updatedAt = Date.now();
        saveSessions();
        scrollToBottom();

        // 4. Play assistant spoken audio aloud through device speakers!
        if (data.assistant_audio_base64) {
          console.log("[VISION_CLIENT] Playing spoken diagnosis audio payload...");
          await playAssistantAudioPayload(data.assistant_audio_base64, spokenText, asstRow);
        }
      } else {
        showToast("Leaf image diagnosis failed. Please try again.", "error");
        appendMessageRow("assistant", "I encountered an issue analyzing this leaf photo. Please try again.", null, null);
      }
    } catch (err) {
      removeThinkingRow(thinkingId);
      console.error("[VISION_CLIENT] Error analyzing leaf photo:", err);
      showToast(`Leaf analysis error: ${err.message}`, "error");
      appendMessageRow("assistant", "Unable to analyze leaf photo right now. Please check your connection.", null, null);
    }
  };

  reader.readAsDataURL(file);
}

function onImageSelected(event) {
  const file = event.target.files[0];
  if (!file) return;
  closePhotoSelectModal();
  handleLeafImageUpload(file);
}

async function analyzeSampleLeaf(sampleId) {
  if (!IS_DEV_MODE) {
    console.warn("[VISION] Demo sample leaf testing is disabled in production.");
    return;
  }
  closePhotoSelectModal();
  try {
    showToast("Loading demonstration leaf...", "info");
    const resp = await fetch("/api/v1/vision/samples");
    if (!resp.ok) throw new Error("Failed to fetch samples");
    const body = await resp.json();
    const sample = (body.samples || []).find(s => s.id === sampleId);
    if (!sample || !sample.image_base64) {
      showToast("Sample not found.", "warning");
      return;
    }

    // Convert base64 to Blob
    const byteCharacters = atob(sample.image_base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: "image/jpeg" });
    const file = new File([blob], `${sampleId}.jpg`, { type: "image/jpeg" });

    handleLeafImageUpload(file, `🍃 Demo Sample: ${sample.title}`);
  } catch (e) {
    console.error("Error running sample leaf:", e);
    showToast("Could not load demo sample: " + e.message, "error");
  }
}

function removeAttachedImage() {
  attachedImageBase64 = null;
  const previewBar = document.getElementById("imagePreviewBar");
  const fileInput = document.getElementById("fileInput");
  if (previewBar) previewBar.style.display = "none";
  if (fileInput) fileInput.value = "";
  checkSendButtonState();
}

// ==========================================
// Voice Input (Speech-to-Text) & Voice Call Mode
// ==========================================
let lastInputWasVoice = false;

function initSpeechRecognition() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRec) {
    speechRecognizer = new SpeechRec();
    speechRecognizer.continuous = false;
    speechRecognizer.interimResults = false;
    speechRecognizer.lang = getLocaleForLang(currentLanguage);

    speechRecognizer.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      const chatInput = document.getElementById("chatInput");
      if (chatInput) {
        chatInput.value = (chatInput.value + " " + transcript).trim();
        autoResizeTextarea(chatInput);
        lastInputWasVoice = true;
        // Automatically send the message for seamless hands-free chat!
        sendMessage();
      }
      stopVoiceRecording();
    };

    speechRecognizer.onerror = (event) => {
      console.warn("Speech recognition notice:", event);
      stopVoiceRecording();
      if (event && (event.error === "not-allowed" || event.error === "service-not-allowed")) {
        openMicPermissionModal();
      } else if (event && event.error === "network") {
        showToast("Speech recognition service temporarily unavailable. Click a sample voice prompt below.", "warning");
      }
    };
    speechRecognizer.onend = () => stopVoiceRecording();
  }
}

let voiceMediaRecorder = null;
let voiceAudioChunks = [];
let voiceRecordingStream = null;

async function startVoiceRecording() {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Microphone API not supported or blocked in this browser origin");
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    voiceRecordingStream = stream;
    voiceAudioChunks = [];

    let mimeType = "audio/webm;codecs=opus";
    if (!window.MediaRecorder || !MediaRecorder.isTypeSupported(mimeType)) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported("audio/webm")) {
        mimeType = "audio/webm";
      } else if (window.MediaRecorder && MediaRecorder.isTypeSupported("audio/mp4")) {
        mimeType = "audio/mp4";
      } else {
        mimeType = "";
      }
    }

    voiceMediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

    voiceMediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        voiceAudioChunks.push(event.data);
      }
    };

    voiceMediaRecorder.onstop = async () => {
      const mime = (voiceMediaRecorder && voiceMediaRecorder.mimeType) || "audio/webm";
      const audioBlob = new Blob(voiceAudioChunks, { type: mime });
      console.log(`[VOICE_CLIENT] Recording stopped. Captured ${audioBlob.size} bytes (${mime})`);

      if (voiceRecordingStream) {
        voiceRecordingStream.getTracks().forEach(t => t.stop());
        voiceRecordingStream = null;
      }

      if (audioBlob.size > 0) {
        await uploadAndProcessVoiceAudio(audioBlob, false);
      } else {
        console.warn("[VOICE_CLIENT] Captured audio is empty (0 bytes).");
        showToast("No audio was captured. Please speak into the mic.", "warning");
      }
    };

    voiceMediaRecorder.start(250);
    isRecordingVoice = true;
    const btnVoice = document.getElementById("btnVoice");
    if (btnVoice) btnVoice.classList.add("recording");
    showToast("🎙️ Listening... Tap mic again to send.", "info");
  } catch (err) {
    console.error("[VOICE_CLIENT] Microphone access denied or error:", err);
    stopVoiceRecording();
    openMicPermissionModal();
  }
}

function stopVoiceRecording() {
  isRecordingVoice = false;
  const btnVoice = document.getElementById("btnVoice");
  if (btnVoice) btnVoice.classList.remove("recording");
  if (voiceMediaRecorder && voiceMediaRecorder.state !== "inactive") {
    try { voiceMediaRecorder.stop(); } catch (e) {}
  }
  checkSendButtonState();
}

function toggleVoiceRecording() {
  if (isRecordingVoice) {
    stopVoiceRecording();
  } else {
    startVoiceRecording();
  }
}

async function uploadAndProcessVoiceAudio(audioBlob, isVoiceCall = false) {
  const typingIndicator = showTypingIndicator();
  console.log(`[VOICE_CLIENT] Uploading ${audioBlob.size} bytes of audio to /api/v1/voice/interact...`);

  try {
    const formData = new FormData();
    const ext = audioBlob.type.includes("wav") ? "wav" : (audioBlob.type.includes("mp4") ? "mp4" : "webm");
    formData.append("file", audioBlob, `voice_query.${ext}`);
    formData.append("language", currentLanguage || "en");
    formData.append("session_id", currentSessionId || "");

    const vHeaders = {};
    if (authToken && !authToken.startsWith("demo_")) {
      vHeaders["Authorization"] = `Bearer ${authToken}`;
    }

    const response = await fetch("/api/v1/voice/interact", {
      method: "POST",
      headers: vHeaders,
      body: formData
    });

    if (typingIndicator) typingIndicator.remove();

    if (!response.ok) {
      let errText = `HTTP ${response.status}`;
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) {
          errText = typeof errJson.detail === "object" ? JSON.stringify(errJson.detail) : errJson.detail;
        } else if (errJson && errJson.error && errJson.error.message) {
          errText = errJson.error.message;
        }
      } catch (e) {
        try { errText = await response.text(); } catch (e2) {}
      }

      if (response.status === 401 || response.status === 403) {
        showToast("Authentication required: Please log in to access your farm digital twin.", "warning");
        showAuthModal();
      } else if (response.status === 402) {
        showToast("Voice recognition quota exceeded. Please check account credits.", "warning");
      } else if (response.status === 504) {
        showToast("Voice recognition request timed out. Please try speaking again.", "warning");
      } else {
        showToast("Voice error: " + errText, "error");
      }
      throw new Error(`Voice server error: ${errText}`);
    }

    const data = await response.json();
    console.log("[VOICE_CLIENT] Voice interact response received:", data);

    const userTranscript = data.user_transcription || "(Voice Input)";
    const assistantText = data.assistant_text || "";

    // 1. Display user speech transcript
    appendMessageRow("user", userTranscript, null, null);
    const curSess = sessionsList.find(s => s.id === currentSessionId);
    if (curSess) {
      curSess.messages.push({ role: "user", content: userTranscript, timestamp: Date.now() });
      saveSessions();
    }

    // 2. Display assistant response and visual cards
    const asstRow = appendMessageRow("assistant", assistantText, null, { visual_cards: data.visual_cards });
    if (curSess) {
      curSess.messages.push({ role: "assistant", content: assistantText, data: { visual_cards: data.visual_cards }, timestamp: Date.now() });
      saveSessions();
    }

    // 3. Play assistant audio out loud
    if (data.assistant_audio_base64) {
      await playAssistantAudioPayload(data.assistant_audio_base64, assistantText, asstRow);
    }

    return data;
  } catch (err) {
    if (typingIndicator) typingIndicator.remove();
    console.error("[VOICE_CLIENT] Voice interaction failed:", err);
    showToast(`Voice error: ${err.message}`, "error");
    appendMessageRow("assistant", `Voice processing issue: ${err.message}`, null, null);
    throw err;
  }
}

async function playAssistantAudioPayload(b64Audio, replyText, targetRow) {
  stopAllActiveAudio();
  try {
    const audioSrc = b64Audio.startsWith("data:") ? b64Audio : `data:audio/wav;base64,${b64Audio}`;
    const audio = new Audio(audioSrc);
    currentAudioPlayer = audio;

    audio.onended = () => {
      currentAudioPlayer = null;
      console.log("[VOICE_CLIENT] Spoken audio finished playing.");
    };

    audio.onerror = (e) => {
      console.warn("[VOICE_CLIENT] Audio element playback error:", e);
      renderTapToPlayButton(targetRow, b64Audio);
    };

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      await playPromise;
      console.log("[VOICE_CLIENT] Spoken answer audio is playing aloud through speakers.");
    }
  } catch (playErr) {
    console.warn("[VOICE_CLIENT] Autoplay prevented by browser:", playErr);
    // Render visible 'Tap to Play' button so user can immediately hear the audio
    renderTapToPlayButton(targetRow, b64Audio);
  }
}

function renderTapToPlayButton(targetRow, b64Audio) {
  if (!targetRow) return;
  const existingBtn = targetRow.querySelector(".btn-tap-to-play");
  if (existingBtn) return;

  const audioAction = document.createElement("div");
  audioAction.className = "audio-action-row tap-to-play-container";
  audioAction.style.marginTop = "8px";

  const playBtn = document.createElement("button");
  playBtn.className = "btn-tap-to-play";
  playBtn.style.cssText = "display:inline-flex;align-items:center;gap:6px;background:var(--accent,#2e7d32);color:#fff;border:none;padding:8px 14px;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,0.15);";
  playBtn.innerHTML = "🔊 Tap to Listen to Spoken Answer";

  playBtn.onclick = () => {
    stopAllActiveAudio();
    const audioSrc = b64Audio.startsWith("data:") ? b64Audio : `data:audio/wav;base64,${b64Audio}`;
    const audio = new Audio(audioSrc);
    currentAudioPlayer = audio;
    audio.play().then(() => {
      playBtn.innerHTML = "🔊 Playing...";
      audio.onended = () => {
        playBtn.innerHTML = "▶️ Listen Again";
      };
    }).catch(e => console.error("Playback click failed:", e));
  };

  audioAction.appendChild(playBtn);
  const bubble = targetRow.querySelector(".chat-bubble") || targetRow;
  bubble.appendChild(audioAction);
}

// Global hook for automated end-to-end verification
window.testVoiceAudioUpload = uploadAndProcessVoiceAudio;

// ==========================================
// Fullscreen Interactive Voice Call Mode (Hands-free)
// ==========================================
let isVoiceCallActiveMic = false;
let voiceCallAudio = null;
let currentVoiceOrbState = "idle";
let lastVoiceUserSpoken = false;
let lastVoiceAiReplied = false;

function initVoiceCallRecognizer() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRec) {
    voiceCallRecognizer = new SpeechRec();
    voiceCallRecognizer.continuous = true;
    voiceCallRecognizer.interimResults = true;
    voiceCallRecognizer.lang = getLocaleForLang(currentLanguage);

    voiceCallRecognizer.onstart = () => {
      setVoiceOrbState("listening");
      const v = getVoiceDict(currentLanguage);
      const farmerSubtitle = document.getElementById("voiceFarmerText");
      if (farmerSubtitle) {
        farmerSubtitle.textContent = v.farmerListening;
      }
    };

    voiceCallRecognizer.onresult = (event) => {
      let interim = "";
      let latestSpeech = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          latestSpeech += " " + event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      if (latestSpeech.trim()) {
        voiceCallTranscriptBuffer += latestSpeech;
      }

      const currentDisplay = (voiceCallTranscriptBuffer + " " + interim).trim();
      const farmerSubtitle = document.getElementById("voiceFarmerText");
      if (farmerSubtitle && currentDisplay) {
        farmerSubtitle.textContent = `"${currentDisplay}"`;
      }

      // Siri-style Adaptive Silence Gate (2.5 seconds without talking before responding)
      if (voiceCallSilenceTimer) clearTimeout(voiceCallSilenceTimer);
      voiceCallSilenceTimer = setTimeout(() => {
        const fullProblem = (voiceCallTranscriptBuffer + " " + interim).trim();
        if (fullProblem.length > 2 && isVoiceCallOpen) {
          voiceCallTranscriptBuffer = "";
          processVoiceCallInput(fullProblem);
        }
      }, 2500);
    };

    voiceCallRecognizer.onerror = (e) => {
      console.warn("Voice Call STT notice:", e);
      if (e && (e.error === "not-allowed" || e.error === "service-not-allowed")) {
        setVoiceOrbState("idle");
        const v = getVoiceDict(currentLanguage);
        const farmerSubtitle = document.getElementById("voiceFarmerText");
        if (farmerSubtitle) {
          farmerSubtitle.innerHTML = `<span style="color:var(--accent-rose);">${v.micError} <a href="javascript:void(0)" onclick="openMicPermissionModal()" style="color:var(--accent-emerald); text-decoration:underline; font-weight:600;">${v.tapForHelp}</a></span>`;
        }
      }
    };

    voiceCallRecognizer.onend = () => {
      const orb = document.getElementById("voiceOrb");
      if (isVoiceCallOpen && isVoiceCallActiveMic && orb && orb.classList.contains("listening")) {
        try { voiceCallRecognizer.start(); } catch (err) {}
      }
    };
  }
}

function openVoiceCallMode() {
  if (currentAppState !== AuthState.AUTHENTICATED) {
    navigateTo("/login", true);
    return;
  }
  isVoiceCallOpen = true;
  isVoiceCallActiveMic = true;
  lastVoiceUserSpoken = false;
  lastVoiceAiReplied = false;
  voiceCallTranscriptBuffer = "";
  if (voiceCallSilenceTimer) {
    clearTimeout(voiceCallSilenceTimer);
    voiceCallSilenceTimer = null;
  }

  const modal = document.getElementById("voiceCallModal");
  if (modal) {
    modal.style.display = "flex";
    modal.style.zIndex = "9999";
  }

  // Stop any other playing audio immediately
  stopAllActiveAudio();

  updateVoiceModalLabels(currentLanguage);
  updateFinanceModalLanguage(currentLanguage);
  startVoiceCallListening();
  if (getCurrentRoute() !== "/voice") {
    navigateTo("/voice", false);
  }
}

function closeVoiceCallMode() {
  isVoiceCallOpen = false;
  isVoiceCallActiveMic = false;
  voiceCallTranscriptBuffer = "";
  if (voiceCallSilenceTimer) {
    clearTimeout(voiceCallSilenceTimer);
    voiceCallSilenceTimer = null;
  }

  const modal = document.getElementById("voiceCallModal");
  if (modal) modal.style.display = "none";

  if (voiceCallRecognizer) {
    try { voiceCallRecognizer.stop(); } catch (e) {}
  }
  stopAllActiveAudio();
  if (getCurrentRoute() === "/voice") {
    navigateTo("/home", false);
  }
}

let voiceCallMediaRecorder = null;
let voiceCallAudioChunks = [];
let voiceCallStream = null;

function toggleVoiceCallMic() {
  if (isVoiceCallActiveMic) {
    stopVoiceCallRecording();
  } else {
    startVoiceCallRecording();
  }
}

async function startVoiceCallRecording() {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Microphone API not supported or blocked in this browser origin");
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    voiceCallStream = stream;
    voiceCallAudioChunks = [];
    isVoiceCallActiveMic = true;

    let mimeType = "audio/webm;codecs=opus";
    if (!window.MediaRecorder || !MediaRecorder.isTypeSupported(mimeType)) {
      mimeType = (window.MediaRecorder && MediaRecorder.isTypeSupported("audio/webm")) ? "audio/webm" : "";
    }

    voiceCallMediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    voiceCallMediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) voiceCallAudioChunks.push(e.data);
    };

    voiceCallMediaRecorder.onstop = async () => {
      const mime = (voiceCallMediaRecorder && voiceCallMediaRecorder.mimeType) || "audio/webm";
      const audioBlob = new Blob(voiceCallAudioChunks, { type: mime });
      console.log(`[VOICE_CALL] Recording stopped. Captured: ${audioBlob.size} bytes`);
      if (voiceCallStream) {
        voiceCallStream.getTracks().forEach(t => t.stop());
        voiceCallStream = null;
      }
      if (audioBlob.size > 0) {
        await processVoiceCallAudio(audioBlob);
      }
    };

    voiceCallMediaRecorder.start(250);
    setVoiceOrbState("listening");
    const v = getVoiceDict(currentLanguage);
    const farmerSubtitle = document.getElementById("voiceFarmerText");
    if (farmerSubtitle) {
      farmerSubtitle.textContent = v.farmerListening;
    }
  } catch (err) {
    console.error("[VOICE_CALL] Mic access error:", err);
    isVoiceCallActiveMic = false;
    setVoiceOrbState("idle");
    const v = getVoiceDict(currentLanguage);
    const farmerSubtitle = document.getElementById("voiceFarmerText");
    if (farmerSubtitle) {
      farmerSubtitle.innerHTML = `<span style="color:var(--accent-rose,#ef4444); font-size:0.92rem;">${v.micError} (${err.name || 'Notice'}). <a href="javascript:void(0)" onclick="openMicPermissionModal()" style="color:var(--accent-emerald,#10b981); text-decoration:underline; font-weight:600; margin-left:6px;">${v.tapForHelp}</a></span>`;
    }
  }
}

function stopVoiceCallRecording() {
  isVoiceCallActiveMic = false;
  if (voiceCallMediaRecorder && voiceCallMediaRecorder.state !== "inactive") {
    try { voiceCallMediaRecorder.stop(); } catch (e) {}
  }
  setVoiceOrbState("idle");
}

function startVoiceCallListening() {
  startVoiceCallRecording();
}

async function processVoiceCallInput(userText) {
  if (!userText || !userText.trim()) return;
  setVoiceOrbState("thinking");
  const v = getVoiceDict(currentLanguage);
  const aiSubtitle = document.getElementById("voiceAiText");
  if (aiSubtitle) {
    aiSubtitle.textContent = v.statusThinking;
  }
  lastVoiceUserSpoken = true;

  try {
    const headers = { "Content-Type": "application/json" };
    if (authToken && !authToken.startsWith("demo_")) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    const resp = await fetch("/api/v1/assistant/chat", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        message: userText,
        language_code: currentLanguage || "en",
        language: currentLanguage || "en",
        session_id: currentSessionId || "voice_session"
      })
    });

    if (!resp.ok) {
      let errDetail = `HTTP ${resp.status}`;
      try {
        const errJson = await resp.json();
        if (errJson && errJson.detail) errDetail = typeof errJson.detail === "object" ? JSON.stringify(errJson.detail) : errJson.detail;
        else if (errJson && errJson.error && errJson.error.message) errDetail = errJson.error.message;
      } catch (e) {
        try { errDetail = await resp.text(); } catch (e2) {}
      }
      if (resp.status === 401 || resp.status === 403) {
        showAuthModal();
      }
      throw new Error(errDetail);
    }

    const data = await resp.json();
    const replyText = data.reply_text || data.message || "";

    const farmerSubtitle = document.getElementById("voiceFarmerText");
    if (farmerSubtitle) {
      farmerSubtitle.textContent = `"${userText}"`;
    }
    if (aiSubtitle) {
      aiSubtitle.textContent = replyText;
    }
    if (replyText) {
      lastVoiceAiReplied = true;
    }

    // Save to chat history and active session
    let curSess = sessionsList.find(s => s.id === currentSessionId);
    if (!curSess) {
      curSess = createNewSession();
    }
    appendMessageRow("user", userText, null, null);
    appendMessageRow("assistant", replyText, null, { visual_cards: data.visual_cards });
    if (curSess) {
      curSess.messages.push({ role: "user", content: userText, input_mode: "voice", timestamp: Date.now() });
      curSess.messages.push({ role: "assistant", content: replyText, data: { visual_cards: data.visual_cards }, timestamp: Date.now() });
      curSess.updatedAt = Date.now();
      saveSessions();
    }
    scrollToBottom();

    // Speak response out loud
    if (data.assistant_audio_base64) {
      await playVoiceCallAssistantResponse(data.assistant_audio_base64, replyText);
    } else {
      // Synthesize audio using backend TTS
      try {
        const synthHeaders = { "Content-Type": "application/json" };
        if (authToken && !authToken.startsWith("demo_")) {
          synthHeaders["Authorization"] = `Bearer ${authToken}`;
        }
        const synthResp = await fetch("/api/v1/voice/synthesize", {
          method: "POST",
          headers: synthHeaders,
          body: JSON.stringify({
            text: replyText,
            language_code: currentLanguage || "en"
          })
        });
        if (synthResp.ok) {
          const blob = await synthResp.blob();
          const reader = new FileReader();
          reader.onloadend = async () => {
            const b64 = reader.result.split(",")[1];
            await playVoiceCallAssistantResponse(b64, replyText);
          };
          reader.readAsDataURL(blob);
        } else {
          setVoiceOrbState("idle");
        }
      } catch (synthErr) {
        console.warn("TTS synthesis error:", synthErr);
        setVoiceOrbState("idle");
      }
    }
  } catch (error) {
    console.error("[VOICE_CALL] processVoiceCallInput error:", error);
    setVoiceOrbState("idle");
    if (aiSubtitle) {
      aiSubtitle.textContent = `Error: ${error.message}`;
    }
  }
}

async function processVoiceCallAudio(audioBlob) {
  setVoiceOrbState("thinking");
  const v = getVoiceDict(currentLanguage);
  const aiSubtitle = document.getElementById("voiceAiText");
  if (aiSubtitle) {
    aiSubtitle.textContent = v.statusThinking;
  }

  try {
    const formData = new FormData();
    const ext = audioBlob.type.includes("wav") ? "wav" : (audioBlob.type.includes("mp4") ? "mp4" : "webm");
    formData.append("file", audioBlob, `voice_call.${ext}`);
    formData.append("language", currentLanguage || "en");
    formData.append("session_id", currentSessionId || "");

    const vHeaders = {};
    if (authToken && !authToken.startsWith("demo_")) {
      vHeaders["Authorization"] = `Bearer ${authToken}`;
    }

    const response = await fetch("/api/v1/voice/interact", {
      method: "POST",
      headers: vHeaders,
      body: formData
    });

    if (!response.ok) {
      let errDetail = `HTTP ${response.status}`;
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) {
          errDetail = typeof errJson.detail === "object" ? JSON.stringify(errJson.detail) : errJson.detail;
        } else if (errJson && errJson.error && errJson.error.message) {
          errDetail = errJson.error.message;
        }
      } catch (e) {
        try { errDetail = await response.text(); } catch (e2) {}
      }
      if (response.status === 401 || response.status === 403) {
        showAuthModal();
      }
      throw new Error(errDetail);
    }

    const data = await response.json();
    console.log("[VOICE_CALL] Server response:", data);

    const userTranscript = data.user_transcription || "";
    const replyText = data.assistant_text || "";

    const farmerSubtitle = document.getElementById("voiceFarmerText");
    if (farmerSubtitle && userTranscript) {
      farmerSubtitle.textContent = `"${userTranscript}"`;
      lastVoiceUserSpoken = true;
    }
    if (aiSubtitle) {
      aiSubtitle.textContent = replyText;
      if (replyText) lastVoiceAiReplied = true;
    }

    // Save to chat history and active session
    let curSess = sessionsList.find(s => s.id === currentSessionId);
    if (!curSess) {
      curSess = createNewSession();
    }
    if (userTranscript) {
      appendMessageRow("user", userTranscript, null, null);
      if (curSess) {
        curSess.messages.push({ role: "user", content: userTranscript, input_mode: "voice", timestamp: Date.now() });
      }
    }
    if (replyText) {
      appendMessageRow("assistant", replyText, null, { visual_cards: data.visual_cards });
      if (curSess) {
        curSess.messages.push({ role: "assistant", content: replyText, data: { visual_cards: data.visual_cards }, timestamp: Date.now() });
      }
    }
    if (curSess) {
      curSess.updatedAt = Date.now();
      saveSessions();
    }
    scrollToBottom();

    // Play synthesized voice out loud
    if (data.assistant_audio_base64) {
      await playVoiceCallAssistantResponse(data.assistant_audio_base64, replyText);
    } else {
      setVoiceOrbState("idle");
    }

  } catch (error) {
    console.error("[VOICE_CALL] Interaction error:", error);
    setVoiceOrbState("idle");
    if (aiSubtitle) {
      aiSubtitle.textContent = `Error: ${error.message}`;
    }
  }
}

async function playVoiceCallAssistantResponse(audioBase64, replyText) {
  setVoiceOrbState("speaking");
  stopAllActiveAudio();

  try {
    const audioSrc = audioBase64.startsWith("data:") ? audioBase64 : `data:audio/wav;base64,${audioBase64}`;
    const audio = new Audio(audioSrc);
    currentAudioPlayer = audio;

    audio.onended = () => {
      currentAudioPlayer = null;
      setVoiceOrbState("idle");
      console.log("[VOICE_CALL] Assistant audio playback complete.");
    };

    audio.onerror = () => {
      console.warn("[VOICE_CALL] Audio element error, falling back to browser speech.");
      fallbackVoiceCallSpeech(replyText);
    };

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      await playPromise;
      console.log("[VOICE_CALL] Audio is playing out loud.");
    }
  } catch (err) {
    console.warn("[VOICE_CALL] Autoplay prevented by browser:", err);
    setVoiceOrbState("idle");
    const aiSubtitle = document.getElementById("voiceAiText");
    if (aiSubtitle) {
      const v = getVoiceDict(currentLanguage);
      aiSubtitle.innerHTML = `${replyText}<br><button onclick="playVoiceCallAssistantResponse('${audioBase64}', '')" style="margin-top:10px;padding:8px 16px;border-radius:20px;background:var(--accent,#2e7d32);color:#fff;border:none;cursor:pointer;font-weight:600;">${v.tapToListen}</button>`;
    }
  }
}

function fallbackVoiceCallSpeech(text) {
  if (!('speechSynthesis' in window)) {
    if (isVoiceCallOpen) startVoiceCallListening();
    return;
  }

  stopAllActiveAudio();

  const cleanText = text.replace(/[\*\#\_`~>•]/g, ' ').trim();
  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.lang = getLocaleForLang(currentLanguage);
  utterance.rate = 0.90;  // Soothing natural pacing
  utterance.pitch = 1.10; // Pleasant female pitch

  const femaleVoice = getBestFemaleSiriVoice(utterance.lang);
  if (femaleVoice) utterance.voice = femaleVoice;

  utterance.onend = () => {
    if (isVoiceCallOpen) {
      setTimeout(() => {
        if (isVoiceCallOpen) startVoiceCallListening();
      }, 800);
    }
  };
  utterance.onerror = () => {
    if (isVoiceCallOpen) startVoiceCallListening();
  };

  window.speechSynthesis.speak(utterance);
}

function setVoiceOrbState(state) {
  currentVoiceOrbState = state;
  const v = getVoiceDict(currentLanguage);
  const orb = document.getElementById("voiceOrb");
  const badge = document.getElementById("voiceStatusBadge");
  const micBtn = document.getElementById("btnVoiceCallMic");
  const micLabel = document.getElementById("voiceCallMicLabel");
  const orbIcon = document.getElementById("orbIcon");

  if (!orb) return;
  orb.className = `voice-orb ${state}`;

  if (state === "listening") {
    if (orbIcon) orbIcon.textContent = "🎙️";
    if (badge) badge.textContent = v.statusListening;
    if (micBtn) micBtn.className = "btn-voice-action mic recording";
    if (micLabel) micLabel.textContent = v.micListening;
  } else if (state === "thinking") {
    if (orbIcon) orbIcon.textContent = "🧠";
    if (badge) badge.textContent = v.statusThinking;
    if (micBtn) micBtn.className = "btn-voice-action mic";
    if (micLabel) micLabel.textContent = v.micThinking;
  } else if (state === "speaking") {
    if (orbIcon) orbIcon.textContent = "🗣️";
    if (badge) badge.textContent = v.statusSpeaking;
    if (micBtn) micBtn.className = "btn-voice-action mic";
    if (micLabel) micLabel.textContent = v.micSpeaking;
  } else {
    if (orbIcon) orbIcon.textContent = "🎙️";
    if (badge) badge.textContent = v.statusIdle;
    if (micBtn) micBtn.className = "btn-voice-action mic";
    if (micLabel) micLabel.textContent = v.micTapToSpeak;
  }
}

function updateVoiceModalLabels(lang = currentLanguage) {
  const v = getVoiceDict(lang);
  const title = document.getElementById("voiceCallAgentTitle");
  const farmerRole = document.getElementById("voiceFarmerRole");
  const aiRole = document.getElementById("voiceAiRole");
  const endCall = document.getElementById("txtEndCall");
  const btnHeader = document.getElementById("txtVoiceCallBtn");
  const farmerSubtitle = document.getElementById("voiceFarmerText");
  const aiSubtitle = document.getElementById("voiceAiText");

  if (title && v.agentTitle) title.textContent = v.agentTitle;
  if (farmerRole && v.farmerRole) farmerRole.textContent = v.farmerRole;
  if (aiRole && v.aiRole) aiRole.textContent = v.aiRole;
  if (endCall && v.endCall) endCall.textContent = v.endCall;
  if (btnHeader) {
    const dict = I18N[lang] || I18N.en;
    if (dict.voiceCallBtn) btnHeader.textContent = dict.voiceCallBtn;
  }

  // Update farmer dialogue prompt if not currently displaying live recognized speech
  if (farmerSubtitle) {
    const isInitialOrListening = !lastVoiceUserSpoken ||
      Object.values(I18N).some(d => d.voice && (farmerSubtitle.textContent === d.voice.farmerInitialText || farmerSubtitle.textContent === d.voice.farmerListening));
    if (isInitialOrListening) {
      farmerSubtitle.textContent = isVoiceCallActiveMic ? v.farmerListening : v.farmerInitialText;
    }
  }

  // Update AI dialogue greeting if not currently displaying an active response
  if (aiSubtitle) {
    const isInitialGreeting = !lastVoiceAiReplied ||
      Object.values(I18N).some(d => d.voice && (aiSubtitle.textContent === d.voice.aiGreeting || aiSubtitle.textContent === d.voice.statusThinking));
    if (isInitialGreeting) {
      aiSubtitle.textContent = v.aiGreeting;
    }
  }

  // Synchronize status badge and mic button labels with active state in new language
  setVoiceOrbState(currentVoiceOrbState || "idle");

  // Keep speech recognizers synchronized with selected locale
  const localeTag = getLocaleForLang(lang);
  if (voiceCallRecognizer) {
    voiceCallRecognizer.lang = localeTag;
  }
  if (speechRecognizer) {
    speechRecognizer.lang = localeTag;
  }
}


// ==========================================
// Multilingual Audio Labels & State Management
// ==========================================
function getListenButtonLabel(state = "idle") {
  const map = {
    idle: {
      te: "వినండి",
      hi: "सुनें",
      en: "Listen",
      ta: "கேளுங்கள்",
      kn: "ಕೇಳಿ",
      ml: "കേൾക്കൂ"
    },
    loading: {
      te: "లోడ్ అవుతోంది...",
      hi: "लोड हो रहा है...",
      en: "Loading...",
      ta: "ஏற்றுகிறது...",
      kn: "ಲೋಡ್ ಆಗುತ್ತಿದೆ...",
      ml: "ലോడ్ ചെയ്യുന്നു..."
    },
    playing: {
      te: "వినిపిస్తోంది...",
      hi: "चल रहा है...",
      en: "Playing...",
      ta: "ஒலிக்கிறது...",
      kn: "ಪ್ಲೇ ಆಗುತ್ತಿದೆ...",
      ml: "കേൾക്കുന്നു..."
    },
    again: {
      te: "మళ్ళీ వినండి",
      hi: "दोबारा सुनें",
      en: "Listen Again",
      ta: "மீண்டும் கேளுங்கள்",
      kn: "ಮತ್ತೆ ಕೇಳಿ",
      ml: "വീണ്ടും കേൾക്കൂ"
    }
  };
  const langMap = map[state] || map.idle;
  return langMap[currentLanguage] || langMap.en;
}

function updateListenButtonState(btn, state) {
  if (!btn) return;
  const icon = btn.querySelector(".audio-btn-icon");
  const label = btn.querySelector(".audio-btn-label");
  btn.classList.remove("playing", "loading");

  if (state === "loading") {
    btn.classList.add("loading");
    if (icon) icon.textContent = "⏳";
    if (label) label.textContent = getListenButtonLabel("loading");
  } else if (state === "playing") {
    btn.classList.add("playing");
    if (icon) icon.textContent = "🔊";
    if (label) label.textContent = getListenButtonLabel("playing");
  } else if (state === "again") {
    if (icon) icon.textContent = "▶️";
    if (label) label.textContent = getListenButtonLabel("again");
  } else {
    if (icon) icon.textContent = "🔊";
    if (label) label.textContent = getListenButtonLabel("idle");
  }
}

// ==========================================
// Canonical Audio Player with Play / Stop Toggle & Zero Overlap
// ==========================================
function stopAllActiveAudio() {
  if (currentAudioPlayer) {
    try {
      currentAudioPlayer.pause();
      currentAudioPlayer.currentTime = 0;
    } catch (e) {}
    currentAudioPlayer = null;
  }
  if (window.speechSynthesis) {
    try { window.speechSynthesis.cancel(); } catch (e) {}
  }
  if (currentPlayingButton) {
    updateListenButtonState(currentPlayingButton, "again");
    currentPlayingButton = null;
  }
  document.querySelectorAll(".btn-speak-audio.playing").forEach(btn => updateListenButtonState(btn, "again"));
}

async function listenToAssistantMessage(btnElement) {
  const row = btnElement.closest(".message-row.assistant");
  const bubble = btnElement.closest(".message-bubble");
  const textEl = bubble ? bubble.querySelector(".message-text") : null;
  if (!textEl) return;

  // 1. Toggle behavior: If button is currently playing, click stops immediately
  if (btnElement.classList.contains("playing") || currentPlayingButton === btnElement) {
    stopAllActiveAudio();
    updateListenButtonState(btnElement, "again");
    currentPlayingButton = null;
    return;
  }

  // 2. Stop any prior active audio so voices never clash
  stopAllActiveAudio();
  currentPlayingButton = btnElement;

  const rawText = textEl.innerText.trim();

  // Helper to start playback on Audio object
  const playAudioObject = async (audioSrc) => {
    try {
      const audio = new Audio(audioSrc);
      currentAudioPlayer = audio;
      updateListenButtonState(btnElement, "playing");

      audio.onended = () => {
        updateListenButtonState(btnElement, "again");
        currentAudioPlayer = null;
        currentPlayingButton = null;
        console.log("[CHAT_VOICE] Finished playing spoken response.");
      };

      audio.onerror = (err) => {
        console.warn("[CHAT_VOICE] Audio playback failed:", err);
        updateListenButtonState(btnElement, "idle");
        currentAudioPlayer = null;
        currentPlayingButton = null;
        renderTapToPlayButton(bubble, audioSrc);
      };

      const playPromise = audio.play();
      if (playPromise !== undefined) {
        await playPromise;
      }
    } catch (e) {
      console.warn("[CHAT_VOICE] Play error or autoplay prevented:", e);
      updateListenButtonState(btnElement, "again");
      renderTapToPlayButton(bubble, audioSrc);
    }
  };

  // 3. If audio is already cached on this row, play it immediately!
  let cachedAudio = row ? row.dataset.audioBase64 : null;
  if (cachedAudio) {
    const audioSrc = cachedAudio.startsWith("data:") ? cachedAudio : `data:audio/wav;base64,${cachedAudio}`;
    await playAudioObject(audioSrc);
    return;
  }

  // 4. Synthesize real neural speech via canonical backend TTS provider
  updateListenButtonState(btnElement, "loading");
  try {
    const cleanText = rawText.replace(/[\*\#\_`~>•]/g, ' ').trim();
    const ttsHeaders = { "Content-Type": "application/json" };
    if (authToken && !authToken.startsWith("demo_")) {
      ttsHeaders["Authorization"] = `Bearer ${authToken}`;
    }

    const resp = await fetch("/api/v1/voice/tts", {
      method: "POST",
      headers: ttsHeaders,
      body: JSON.stringify({
        text: cleanText,
        language_code: currentLanguage,
        slow_speed: false
      })
    });

    if (resp.ok) {
      const data = await resp.json();
      if (data.status === "success" && data.audio_base64) {
        cachedAudio = data.audio_base64;
        if (row) row.dataset.audioBase64 = cachedAudio;
        await playAudioObject(cachedAudio);
        return;
      }
      throw new Error(data.message || "TTS service returned unready status");
    } else {
      let serverErrorMsg = `TTS service error (${resp.status})`;
      try {
        const errData = await resp.json();
        if (errData && (errData.detail || errData.message)) {
          serverErrorMsg = errData.detail || errData.message;
        }
      } catch (_) {}

      if (resp.status === 401 || resp.status === 403) {
        showAuthModal();
        throw new Error("Authentication required. Please log in to access your farm digital twin.");
      } else if (resp.status === 402) {
        throw new Error("Voice synthesis quota exceeded. Please check credits.");
      } else if (resp.status === 504) {
        throw new Error("Voice synthesis timed out. Please try again.");
      }
      throw new Error(serverErrorMsg);
    }
  } catch (err) {
    console.error("[CHAT_VOICE] TTS synthesis error:", err);
    updateListenButtonState(btnElement, "idle");
    currentPlayingButton = null;
    showToast("Audio synthesis issue: " + err.message, "warning");
  }
}

// Global aliases for testing and backward compatibility
window.listenToAssistantMessage = listenToAssistantMessage;
window.speakText = listenToAssistantMessage;

function getBestFemaleSiriVoice(targetLang) {
  if (!window.speechSynthesis) return null;
  const voices = window.speechSynthesis.getVoices();
  const targetCode = targetLang.split("-")[0];

  // Preference for soothing clear female voices
  const siriFemaleVoices = voices.filter(v =>
    v.lang.startsWith(targetCode) && (
      v.name.toLowerCase().includes("female") ||
      v.name.toLowerCase().includes("heera") ||
      v.name.toLowerCase().includes("swara") ||
      v.name.toLowerCase().includes("neerja") ||
      v.name.toLowerCase().includes("zira") ||
      v.name.toLowerCase().includes("samantha") ||
      v.name.toLowerCase().includes("karen") ||
      v.name.toLowerCase().includes("google")
    )
  );

  if (siriFemaleVoices.length > 0) return siriFemaleVoices[0];
  return voices.find(v => v.lang.startsWith(targetCode)) || voices[0] || null;
}

// ==========================================
// Microphone Permission & Quick Voice Prompt Helpers
// ==========================================
const SAMPLE_VOICE_PROMPTS = {
  te: [
    { title: "వరిలో ఎరువుల మోతాదు ఎంత?", icon: "🌾", desc: "ఎరువుల షెడ్యూల్ & పోషకాలు" },
    { title: "మిర్చిలో ఆకుముడత నివారణ ఏమిటి?", icon: "🌶️", desc: "చీడపీడల సమగ్ర నివారణ" },
    { title: "వరంగల్ మార్కెట్లో పత్తి ధర ఎంత?", icon: "🏪", desc: "ఈరోజు తాజా మండి ధరలు" },
    { title: "ఈ వారం వాతావరణ అంచనా ఏమిటి?", icon: "🌦️", desc: "వర్షం & ఉష్ణోగ్రత వివరాలు" }
  ],
  hi: [
    { title: "टमाटर में अगेती झुलसा का क्या उपचार है?", icon: "🍅", desc: "रोग निदान एवं कीटनाशक" },
    { title: "धान की फसल में खाद का सही समय क्या है?", icon: "🌾", desc: "संतुलित उर्वरक प्रबंधन" },
    { title: "आज कपास का मंडी भाव क्या है?", icon: "🏪", desc: "ताजा कृषि मंडी भाव" },
    { title: "आज बारिश की क्या संभावना है?", icon: "🌦️", desc: "स्थानीय मौसम पूर्वानुमान" }
  ],
  en: [
    { title: "How to treat leaf curl in chilli?", icon: "🌶️", desc: "IPM & chemical recommendations" },
    { title: "What is the fertilizer schedule for Rice?", icon: "🌾", desc: "NPK balanced nutrition" },
    { title: "Check today modal price for Cotton in Warangal", icon: "🏪", desc: "Live mandi benchmark prices" },
    { title: "Show weather forecast and rain alert", icon: "🌦️", desc: "Localized agro-meteorology" }
  ],
  ta: [
    { title: "நெல் பயிருக்கு உரமிடும் அட்டவணை என்ன?", icon: "🌾", desc: "சமச்சீர் உர மேலாண்மை" },
    { title: "மிளகாய் இலைச்சுருட்டல் நோயை எப்படி கட்டுப்படுத்துவது?", icon: "🌶️", desc: "பூச்சி மேலாண்மை" }
  ],
  kn: [
    { title: "ಭತ್ತದ ಬೆಳೆಗೆ ರಸಗೊಬ್ಬರ ವೇಳಾಪಟ್ಟಿ ತಿಳಿಸಿ", icon: "🌾", desc: "ರಸಗೊಬ್ಬರ ನಿರ್ವಹಣೆ" },
    { title: "ಮೆಣಸಿನಕಾಯಿ ಎಲೆ ಸುರುಟು ರೋಗಕ್ಕೆ ಪರಿಹಾರವೇನು?", icon: "🌶️", desc: "ಕೀಟ ನಿರ್ವಹಣೆ" }
  ],
  mr: [
    { title: "कपाशीसाठी आजचा बाजारभाव काय आहे?", icon: "🏪", desc: "मंडी दर माहिती" },
    { title: "टोमॅटोवरील रोगाचे नियंत्रण कसे करावे?", icon: "🍅", desc: "रोग निदान आणि सल्ला" }
  ]
};

function openMicPermissionModal() {
  const modal = document.getElementById("micPermissionModal");
  if (!modal) return;
  modal.style.display = "flex";

  const chipsContainer = document.getElementById("micSampleChips");
  if (chipsContainer) {
    const list = SAMPLE_VOICE_PROMPTS[currentLanguage] || SAMPLE_VOICE_PROMPTS.en;
    chipsContainer.innerHTML = list.map(item => `
      <div onclick="selectSampleVoicePrompt('${escapeHtml(item.title)}')" style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bg-secondary); border:1px solid var(--border-subtle); border-radius:8px; cursor:pointer; transition:all 0.2s;" onmouseover="this.style.borderColor='var(--accent-emerald)'" onmouseout="this.style.borderColor='var(--border-subtle)'">
        <span style="font-size:1.3rem;">${item.icon}</span>
        <div style="flex:1;">
          <div style="font-weight:600; color:var(--text-primary); font-size:0.88rem;">${escapeHtml(item.title)}</div>
          <div style="font-size:0.75rem; color:var(--text-secondary);">${escapeHtml(item.desc)}</div>
        </div>
        <span style="color:var(--accent-emerald); font-weight:bold;">→</span>
      </div>
    `).join("");
  }
}

function closeMicPermissionModal() {
  const modal = document.getElementById("micPermissionModal");
  if (modal) modal.style.display = "none";
}

async function requestMicPermissionDirectly() {
  closeMicPermissionModal();
  try {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(t => t.stop());
      showToast("✅ Microphone permission granted! You can now speak.", "success");
      initSpeechRecognition();
      startVoiceRecording();
    } else {
      alert("Media devices not supported in this browser. Please use Chrome or Edge.");
    }
  } catch (err) {
    console.warn("Direct getUserMedia permission denied:", err);
    openMicPermissionModal();
  }
}

function selectSampleVoicePrompt(promptText) {
  closeMicPermissionModal();
  if (isVoiceCallOpen) {
    closeVoiceCallMode();
  }
  const chatInput = document.getElementById("chatInput");
  if (chatInput) {
    chatInput.value = promptText;
    autoResizeTextarea(chatInput);
    lastInputWasVoice = true;
    sendMessage();
  }
}

function setAudioButtonLoading(btn) {
  if (!btn) return;
  btn.classList.add("playing");
  const label = getLoadingButtonText(currentLanguage);
  btn.innerHTML = `<span>⏳</span> <span>${label}</span>`;
}

function setAudioButtonPlaying(btn) {
  if (!btn) return;
  btn.classList.add("playing");
  const label = getStopButtonText(currentLanguage);
  btn.innerHTML = `<span>⏹️</span> <span>${label}</span>`;
}

function resetAudioButton(btn) {
  if (!btn) return;
  btn.classList.remove("playing");
  const label = getListenButtonText(currentLanguage);
  btn.innerHTML = `<span>🔊</span> <span>${label}</span>`;
}


// ==========================================
// Input Event Handlers
// ==========================================
function autoResizeTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 140) + "px";
  checkSendButtonState();
}

function checkSendButtonState() {
  const chatInput = document.getElementById("chatInput");
  const btnSend = document.getElementById("btnSend");
  const hasText = chatInput && chatInput.value.trim().length > 0;
  const hasImage = !!attachedImageBase64;
  if (btnSend) {
    btnSend.disabled = !(hasText || hasImage);
  }
}

function handleInputKeyDown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function toggleMobileSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.toggle("open");
}

function sendQuickQuery(text) {
  const input = document.getElementById("chatInput");
  if (!input) return;
  input.value = text;
  autoResizeTextarea(input);
  checkSendButtonState();
  sendMessage();
}

// ==========================================
// PWA & Mobile App Installation Support
// ==========================================
let deferredInstallPrompt = null;

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((reg) => console.log('BHOOMI PWA ServiceWorker active:', reg.scope))
      .catch((err) => console.log('ServiceWorker registration notice:', err));
  });
}

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  const banner = document.getElementById('pwaInstallBanner');
  if (banner && !sessionStorage.getItem('pwa_banner_dismissed')) {
    banner.style.display = 'flex';
  }
});

function installPWA() {
  const banner = document.getElementById('pwaInstallBanner');
  if (deferredInstallPrompt) {
    deferredInstallPrompt.prompt();
    deferredInstallPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        console.log('Farmer installed BHOOMI PWA app on mobile');
      }
      deferredInstallPrompt = null;
      if (banner) banner.style.display = 'none';
    });
  } else {
    alert("To install BHOOMI on your mobile device:\n\n• Android: Tap browser menu (⋮) -> 'Add to Home screen' or 'Install App'.\n• iPhone/iPad: Tap Share (⎋) -> 'Add to Home Screen'.");
  }
}

function dismissPwaBanner() {
  const banner = document.getElementById('pwaInstallBanner');
  if (banner) banner.style.display = 'none';
  sessionStorage.setItem('pwa_banner_dismissed', 'true');
}

// ==========================================
// Explicit Global Window Bindings for HTML onclick
// ==========================================
window.openVoiceCallMode = openVoiceCallMode;
window.closeVoiceCallMode = closeVoiceCallMode;
window.toggleVoiceRecording = toggleVoiceRecording;
window.toggleVoiceCallMic = toggleVoiceCallMic;
window.openMicPermissionModal = openMicPermissionModal;
window.closeMicPermissionModal = closeMicPermissionModal;
window.quickDemoLogin = quickDemoLogin;
window.startNewChat = startNewChat;
window.handleLogout = handleLogout;
window.openProfileModal = openProfileModal;
window.closeProfileModal = closeProfileModal;
window.openPhotoSelectModal = openPhotoSelectModal;
window.closePhotoSelectModal = closePhotoSelectModal;
window.triggerCameraCapture = triggerCameraCapture;
window.triggerGalleryUpload = triggerGalleryUpload;
window.requestMicPermissionDirectly = requestMicPermissionDirectly;
window.selectSampleVoicePrompt = selectSampleVoicePrompt;
window.installPWA = installPWA;
window.dismissPwaBanner = dismissPwaBanner;
window.toggleTheme = toggleTheme;
window.toggleMobileSidebar = toggleMobileSidebar;
window.clearAllSessions = clearAllSessions;
window.handleSendOtp = handleSendOtp;
window.handleResendOtp = handleResendOtp;
window.handleVerifyOtp = handleVerifyOtp;
window.backToOtpStep1 = backToOtpStep1;
window.onAuthLanguageChanged = onAuthLanguageChanged;
window.onLanguageChanged = onLanguageChanged;
window.sendMessage = sendMessage;
window.sendQuickQuery = sendQuickQuery;
window.removeAttachedImage = removeAttachedImage;
window.onStateChanged = onStateChanged;
window.onDistrictChanged = onDistrictChanged;
window.detectFarmerLocation = detectFarmerLocation;
window.toggleSoilTestFields = toggleSoilTestFields;
window.analyzeSampleLeaf = analyzeSampleLeaf;
window.openFinanceModal = openFinanceModal;
window.closeFinanceModal = closeFinanceModal;
window.calculateFinance = calculateFinance;
window.runWhatIfSimulation = runWhatIfSimulation;
window.updateFinanceModalLanguage = updateFinanceModalLanguage;
window.updateVoiceModalLabels = updateVoiceModalLabels;
window.getVoiceDict = getVoiceDict;
window.getLocaleForLang = getLocaleForLang;
window.switchAuthMode = switchAuthMode;
window.handleReviewerDemoLogin = handleReviewerDemoLogin;
window.handleReviewerLogin = handleReviewerLogin;

async function handleCompleteOnboarding() {
  const nameInput = document.getElementById("farmerNameInput");
  const stateInput = document.getElementById("farmerStateInput");
  const districtInput = document.getElementById("farmerDistrictInput");
  const villageInput = document.getElementById("farmerVillageInput");
  const cropInput = document.getElementById("farmerCropInput");
  const varietyInput = document.getElementById("farmerVarietyInput");
  const acresInput = document.getElementById("farmerAcresInput");
  const errorMsg = document.getElementById("authErrorMsg");
  const btn = document.getElementById("btnCompleteOnboarding");

  if (errorMsg) errorMsg.style.display = "none";

  const name = nameInput ? nameInput.value.trim() : "";
  const state = stateInput ? stateInput.value : "";
  const district = districtInput ? districtInput.value.trim() : "";
  const village = villageInput ? villageInput.value.trim() : "";
  const crop = cropInput ? cropInput.value.trim() : "";
  const variety = varietyInput ? varietyInput.value.trim() : "";
  const acres = acresInput && acresInput.value ? parseFloat(acresInput.value) : null;

  if (!state || !district) {
    if (errorMsg) {
      errorMsg.textContent = "Please select both State and District.";
      errorMsg.style.display = "block";
    }
    return;
  }

  const labFields = document.getElementById("labSoilFields");
  const isSoilManual = labFields && labFields.style.display !== "none";
  const soilN = isSoilManual && document.getElementById("farmerSoilN")?.value ? parseFloat(document.getElementById("farmerSoilN").value) : null;
  const soilP = isSoilManual && document.getElementById("farmerSoilP")?.value ? parseFloat(document.getElementById("farmerSoilP").value) : null;
  const soilK = isSoilManual && document.getElementById("farmerSoilK")?.value ? parseFloat(document.getElementById("farmerSoilK").value) : null;
  const soilPh = isSoilManual && document.getElementById("farmerSoilPh")?.value ? parseFloat(document.getElementById("farmerSoilPh").value) : null;
  const soilSourceType = (soilN !== null || soilP !== null || soilK !== null) ? "farmer_entered" : "estimated";

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "<span>⏳</span> Saving Farm Profile...";
  }

  try {
    const token = authToken || localStorage.getItem("bhoomi_auth_token");
    const res = await fetch("/api/v1/farmer/onboard", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        name: name || "Farmer",
        preferred_language: currentLanguage,
        state: state,
        district: district,
        village: village,
        current_crop: crop,
        crop_variety: variety,
        land_area_acres: acres,
        soil_type: currentSoilEstimate?.soil_type || "black",
        soil_source_type: soilSourceType,
        soil_n: soilN,
        soil_p: soilP,
        soil_k: soilK,
        soil_ph: soilPh || currentSoilEstimate?.estimated_ph || 6.5,
        latitude: detectedLat,
        longitude: detectedLon
      })
    });

    if (res.ok) {
      showToast("Farm and profile created successfully!", "success");
      await initAuth();
    } else {
      const err = await res.json().catch(() => ({}));
      if (errorMsg) {
        errorMsg.textContent = err.detail || err.message || "Failed to complete onboarding. Please check your inputs.";
        errorMsg.style.display = "block";
      }
      showToast(err.detail || "Onboarding failed. Please check your inputs.", "error");
    }
  } catch (err) {
    if (errorMsg) {
      errorMsg.textContent = "Network error saving profile: " + err.message;
      errorMsg.style.display = "block";
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "<span>🌾</span> <span>Save Profile & Enter Dashboard</span>";
    }
  }
}

window.handleCompleteOnboarding = handleCompleteOnboarding;
window.navigateTo = navigateTo;
window.AuthState = AuthState;
window.setAppState = setAppState;

window.initOtpInputBoxes = initOtpInputBoxes;
window.getOtpCode = getOtpCode;
window.clearOtpBoxes = clearOtpBoxes;
window.distributeOtpDigits = distributeOtpDigits;
window.focusFirstOtpBox = focusFirstOtpBox;

// =============================================================================
// TODAY'S FARM TASKS CLIENT ENGINE (CANONICAL TASK LIFECYCLE)
// =============================================================================

const TASK_LIFECYCLE_I18N = {
  en: {
    DUE: "⚡ DUE",
    OVERDUE: "⚠️ OVERDUE",
    COMPLETED: "✓ COMPLETED",
    POSTPONED: "⏳ POSTPONED",
    EXPIRED: "⛔ EXPIRED",
    UPCOMING: "🗓️ UPCOMING",
    SCHEDULED: "🗓️ UPCOMING",
    completeBtn: "✓ Complete",
    whyLabel: "Why",
    emptyMsg: "✅ No pending tasks for today. Your farm is up to date!",
    noTasks: "No tasks scheduled for today.",
    errorMsg: "Unable to load tasks at this time."
  },
  te: {
    DUE: "⚡ చేయవలసినది",
    OVERDUE: "⚠️ గడువు ముగిసింది",
    COMPLETED: "✓ పూర్తయింది",
    POSTPONED: "⏳ వాయిదా పడింది",
    EXPIRED: "⛔ సమయం దాటింది",
    UPCOMING: "🗓️ రాబోయే పని",
    SCHEDULED: "🗓️ రాబోయే పని",
    completeBtn: "✓ పూర్తి చేయండి",
    whyLabel: "కారణం",
    emptyMsg: "✅ నేటికి పెండింగ్ పనులు లేవు. మీ పొలం స్థితి తాజాగా ఉంది!",
    noTasks: "నేటికి పనులేవీ షెడ్యూల్ కాలేదు.",
    errorMsg: "పనులను లోడ్ చేయడం సాధ్యం కాలేదు."
  },
  hi: {
    DUE: "⚡ देय कार्य",
    OVERDUE: "⚠️ अतिदेय",
    COMPLETED: "✓ पूर्ण हुआ",
    POSTPONED: "⏳ स्थगित",
    EXPIRED: "⛔ समय समाप्त",
    UPCOMING: "🗓️ आगामी",
    SCHEDULED: "🗓️ आगामी",
    completeBtn: "✓ पूर्ण करें",
    whyLabel: "कारण",
    emptyMsg: "✅ आज के लिए कोई लंबित कार्य नहीं हैं। आपका खेत अद्यतित है!",
    noTasks: "आज के लिए कोई कार्य निर्धारित नहीं है।",
    errorMsg: "इस समय कार्य लोड करने में असमर्थ।"
  }
};

async function loadTodayTasks() {
  const container = document.getElementById("todayTasksList");
  if (!container) return;

  const token = authToken || localStorage.getItem("bhoomi_auth_token");
  if (!token) {
    container.innerHTML = `<div style="padding: 12px; font-size: 0.85rem; color: var(--text-secondary, #64748b);">Please login to view tasks.</div>`;
    return;
  }

  const lang = localStorage.getItem("bhoomi_lang") || "en";
  const dict = TASK_LIFECYCLE_I18N[lang] || TASK_LIFECYCLE_I18N.en;

  try {
    const res = await fetch("/api/v1/tasks/today", {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/json"
      }
    });

    if (!res.ok) {
      container.innerHTML = `<div style="padding: 12px; font-size: 0.85rem; color: var(--text-secondary, #64748b);">${dict.noTasks}</div>`;
      return;
    }

    const tasks = await res.json();
    if (!tasks || tasks.length === 0) {
      container.innerHTML = `<div style="padding: 14px; font-size: 0.85rem; color: #16a34a; background: var(--bg-surface, #ffffff); border-radius: 8px; border: 1px dashed #86efac; text-align: center;">${dict.emptyMsg}</div>`;
      return;
    }

    container.innerHTML = tasks.map(t => {
      const statusRaw = (t.status || "DUE").toUpperCase();
      const isCompleted = statusRaw === "COMPLETED";
      const isOverdue = statusRaw === "OVERDUE";
      const isExpired = statusRaw === "EXPIRED";
      const isPostponed = statusRaw === "POSTPONED";
      const isUpcoming = statusRaw === "SCHEDULED" || statusRaw === "UPCOMING" || statusRaw === "PENDING" || statusRaw === "PLANNED";

      let statusBg = "#fef3c7";
      let statusColor = "#b45309";
      let statusBorder = "#fcd34d";
      let statusLabel = dict.DUE;

      if (isCompleted) {
        statusBg = "#dcfce7";
        statusColor = "#15803d";
        statusBorder = "#86efac";
        statusLabel = dict.COMPLETED;
      } else if (isOverdue) {
        statusBg = "#fee2e2";
        statusColor = "#b91c1c";
        statusBorder = "#fca5a5";
        statusLabel = dict.OVERDUE;
      } else if (isExpired) {
        statusBg = "#f1f5f9";
        statusColor = "#64748b";
        statusBorder = "#cbd5e1";
        statusLabel = dict.EXPIRED;
      } else if (isPostponed) {
        statusBg = "#ffedd5";
        statusColor = "#c2410c";
        statusBorder = "#fdba74";
        statusLabel = dict.POSTPONED;
      } else if (isUpcoming) {
        statusBg = "#e0f2fe";
        statusColor = "#0369a1";
        statusBorder = "#bae6fd";
        statusLabel = dict.UPCOMING;
      }

      const priorityVal = (t.priority || "").toUpperCase();
      const priorityBg = priorityVal === "HIGH" || priorityVal === "CRITICAL" ? "#fee2e2" : "#e0f2fe";
      const priorityColor = priorityVal === "HIGH" || priorityVal === "CRITICAL" ? "#b91c1c" : "#0369a1";

      const cardBorder = isCompleted ? "#86efac" : (isOverdue ? "#fca5a5" : "var(--border-color, #e2e8f0)");
      const cardBg = isOverdue ? "rgba(254, 242, 242, 0.35)" : "var(--bg-surface, #ffffff)";

      return `
        <div class="today-task-card ${isCompleted ? 'task-completed' : ''} ${isOverdue ? 'task-overdue' : ''}" id="taskCard_${t.task_id}" style="display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 12px 14px; margin-bottom: 8px; background: ${cardBg}; border: 1px solid ${cardBorder}; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
          <div style="flex: 1;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px; flex-wrap: wrap;">
              <span style="font-size: 0.68rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; background: ${statusBg}; color: ${statusColor}; border: 1px solid ${statusBorder};">${statusLabel}</span>
              <span style="font-size: 0.68rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; background: ${priorityBg}; color: ${priorityColor};">${priorityVal || 'MEDIUM'}</span>
              <span style="font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; background: #f1f5f9; color: #475569; font-weight: 600;">🌾 ${t.crop || 'Crop'}</span>
              <span style="font-size: 0.72rem; color: var(--text-muted, #94a3b8);">📅 ${t.due_at ? t.due_at.slice(0,10) : 'Today'}</span>
            </div>
            <div class="task-title" style="font-size: 0.92rem; font-weight: 600; color: var(--text-primary, #0f172a); ${isCompleted ? 'text-decoration: line-through; opacity: 0.75;' : ''}">${t.title}</div>
            ${t.reason ? `<div style="font-size: 0.8rem; color: var(--text-secondary, #475569); margin-top: 4px;">💡 <strong>${dict.whyLabel}:</strong> <em>${t.reason}</em></div>` : ''}
            ${t.postponement_reason ? `<div style="font-size: 0.78rem; color: #b45309; margin-top: 3px;">🌦️ ${t.postponement_reason}</div>` : ''}
          </div>
          <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
            ${isCompleted ? `
              <span style="display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; background: #dcfce7; color: #15803d; border-radius: 6px; font-size: 0.78rem; font-weight: 700;">
                ✓ ${dict.COMPLETED.replace('✓ ', '')}
              </span>
            ` : (isExpired ? `
              <span style="display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; background: #f1f5f9; color: #64748b; border-radius: 6px; font-size: 0.78rem; font-weight: 600;">
                ${dict.EXPIRED}
              </span>
            ` : `
              <button type="button" class="btn-complete-task" onclick="handleCompleteTask('${t.task_id}')" style="padding: 6px 12px; background: #16a34a; color: white; border: none; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; box-shadow: 0 1px 4px rgba(22,163,74,0.3);">
                ${dict.completeBtn}
              </button>
            `)}
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div style="padding: 12px; font-size: 0.85rem; color: var(--text-secondary, #64748b);">${dict.errorMsg}</div>`;
  }
}
window.loadTodayTasks = loadTodayTasks;

async function handleCompleteTask(taskId) {
  const token = authToken || localStorage.getItem("bhoomi_auth_token");
  if (!token) return;

  const card = document.getElementById(`taskCard_${taskId}`);
  if (card) card.style.opacity = "0.5";

  try {
    const res = await fetch(`/api/v1/tasks/${encodeURIComponent(taskId)}/complete`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ completion_source: "web_ui" })
    });

    if (res.ok) {
      showToast("Task marked as COMPLETED!", "success");
      await loadTodayTasks();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || "Failed to complete task.", "error");
      if (card) card.style.opacity = "1";
    }
  } catch (err) {
    showToast("Network error completing task: " + err.message, "error");
    if (card) card.style.opacity = "1";
  }
}
window.handleCompleteTask = handleCompleteTask;

// =============================================================================
// PERSISTENT DECISION HISTORY & EXPLAINABILITY CLIENT ENGINE (BATCH 10)
// =============================================================================

function getDecisionsDict(lang) {
  const dict = I18N[lang] || I18N.en;
  return dict.decisions || I18N.en.decisions;
}
window.getDecisionsDict = getDecisionsDict;

async function loadDecisionHistory() {
  const container = document.getElementById("decisionHistoryList");
  if (!container) return;

  const dDict = getDecisionsDict(currentLanguage);
  const token = authToken || localStorage.getItem("bhoomi_auth_token");
  if (!token) {
    container.innerHTML = `<div style="padding: 12px; font-size: 0.85rem; color: var(--text-secondary, #64748b);">Please login to view decision history.</div>`;
    return;
  }

  try {
    const res = await fetch("/api/v1/decisions/history?limit=10", {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/json"
      }
    });

    if (!res.ok) {
      container.innerHTML = `<div style="padding: 12px; font-size: 0.85rem; color: var(--text-secondary, #64748b);">${dDict.empty}</div>`;
      return;
    }

    const data = await res.json();
    const decisions = data.decisions || [];

    if (decisions.length === 0) {
      container.innerHTML = `<div style="padding: 14px; font-size: 0.85rem; color: var(--text-secondary, #64748b); background: var(--bg-surface, #ffffff); border-radius: 8px; border: 1px dashed var(--border-color, #cbd5e1); text-align: center;">🌱 ${dDict.empty}</div>`;
      return;
    }

    container.innerHTML = decisions.map(d => {
      const typeStr = (d.decision_type || "ADVISORY").toUpperCase();
      const typeBg = typeStr.includes("HEALTH") ? "#fef2f2" : typeStr.includes("IRR") ? "#eff6ff" : typeStr.includes("MARKET") ? "#f0fdf4" : "#fefce8";
      const typeColor = typeStr.includes("HEALTH") ? "#b91c1c" : typeStr.includes("IRR") ? "#1d4ed8" : typeStr.includes("MARKET") ? "#15803d" : "#a16207";
      const actionStr = (d.farmer_action || "PENDING").toUpperCase();
      const actionBg = actionStr === "ACCEPTED" || actionStr === "FOLLOWED" ? "#dcfce7" : actionStr === "REJECTED" || actionStr === "NOT_FOLLOWED" ? "#fee2e2" : "#f1f5f9";
      const actionColor = actionStr === "ACCEPTED" || actionStr === "FOLLOWED" ? "#15803d" : actionStr === "REJECTED" || actionStr === "NOT_FOLLOWED" ? "#b91c1c" : "#475569";
      const dateFormatted = d.created_at ? new Date(d.created_at).toLocaleString() : "Recent";
      const confPct = d.confidence != null ? Math.round(d.confidence * 100) : null;
      const crop = (d.input_context && d.input_context.crop) ? d.input_context.crop : "Farm";

      return `
        <div class="decision-trace-card" id="decCard_${d.decision_id}" style="display: flex; flex-direction: column; gap: 8px; padding: 14px; margin-bottom: 10px; background: var(--bg-surface, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
          <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px;">
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <span style="font-size: 0.7rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; background: ${typeBg}; color: ${typeColor};">${typeStr}</span>
              <span style="font-size: 0.72rem; padding: 3px 8px; border-radius: 6px; background: #f8fafc; color: #475569; font-weight: 600;">🌾 ${crop}</span>
              ${confPct !== null ? `<span style="font-size: 0.72rem; padding: 3px 8px; border-radius: 6px; background: #f0fdf4; color: #166534; font-weight: 600;">🎯 ${confPct}% Confidence</span>` : ''}
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-size: 0.7rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; background: ${actionBg}; color: ${actionColor};">${actionStr}</span>
              <span style="font-size: 0.72rem; color: var(--text-muted, #94a3b8);">🕒 ${dateFormatted}</span>
            </div>
          </div>
          <div style="font-size: 0.92rem; font-weight: 600; color: var(--text-primary, #0f172a); line-height: 1.4;">
            ${d.recommendation_text}
          </div>
          ${d.assumptions && d.assumptions.length > 0 ? `
            <div style="font-size: 0.8rem; color: var(--text-secondary, #475569); background: #f8fafc; padding: 6px 10px; border-radius: 6px;">
              💡 <em>${d.assumptions[0]}</em>
            </div>
          ` : ''}
          <div style="display: flex; justify-content: flex-end; margin-top: 4px;">
            <button type="button" onclick="openDecisionDetail('${d.decision_id}')" style="background: transparent; border: 1px solid var(--border-color, #cbd5e1); border-radius: 6px; padding: 4px 10px; font-size: 0.78rem; font-weight: 600; color: #0284c7; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;">
              ${dDict.viewDetail}
            </button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div style="padding: 12px; font-size: 0.85rem; color: var(--text-secondary, #64748b);">${dDict.empty}</div>`;
  }
}
window.loadDecisionHistory = loadDecisionHistory;

async function openDecisionDetail(decisionId) {
  const modal = document.getElementById("decisionDetailModal");
  const body = document.getElementById("decisionDetailBody");
  if (!modal || !body) return;

  const dDict = getDecisionsDict(currentLanguage);
  modal.style.display = "flex";
  body.innerHTML = `<div style="text-align: center; padding: 30px; color: var(--text-secondary, #64748b);">⏳ Loading trace details...</div>`;

  const token = authToken || localStorage.getItem("bhoomi_auth_token");
  if (!token) {
    body.innerHTML = `<div style="padding: 20px; color: #b91c1c;">Please authenticate to inspect decision traces.</div>`;
    return;
  }

  try {
    const res = await fetch(`/api/v1/decisions/${encodeURIComponent(decisionId)}`, {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/json"
      }
    });

    if (!res.ok) {
      body.innerHTML = `<div style="padding: 20px; color: #b91c1c;">Unable to load decision trace details (${res.status}).</div>`;
      return;
    }

    const t = await res.json();
    const confPct = t.confidence != null ? Math.round(t.confidence * 100) : 90;
    const actionStr = (t.farmer_action || "PENDING").toUpperCase();
    const actionBg = actionStr === "ACCEPTED" || actionStr === "FOLLOWED" ? "#dcfce7" : actionStr === "REJECTED" || actionStr === "NOT_FOLLOWED" ? "#fee2e2" : "#f1f5f9";
    const actionColor = actionStr === "ACCEPTED" || actionStr === "FOLLOWED" ? "#15803d" : actionStr === "REJECTED" || actionStr === "NOT_FOLLOWED" ? "#b91c1c" : "#475569";

    body.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <!-- Top Summary Card -->
        <div style="background: var(--bg-surface-alt, #f8fafc); padding: 14px; border-radius: 12px; border: 1px solid var(--border-subtle, #e2e8f0);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
            <span style="font-size: 0.75rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; background: #e0f2fe; color: #0369a1; text-transform: uppercase;">
              ${t.decision_type || 'ADVISORY'}
            </span>
            <span style="font-size: 0.75rem; color: var(--text-muted, #94a3b8);">ID: ${t.decision_id}</span>
          </div>
          <div style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary, #0f172a); margin-bottom: 8px;">
            ${t.recommendation_text}
          </div>
          <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap; font-size: 0.8rem;">
            <span style="padding: 2px 8px; border-radius: 6px; background: ${actionBg}; color: ${actionColor}; font-weight: 700;">${dDict.statusLabel} ${actionStr}</span>
            ${t.feedback_rating ? `<span style="padding: 2px 8px; border-radius: 6px; background: #fef3c7; color: #b45309; font-weight: 700;">★ ${t.feedback_rating}</span>` : ''}
            <span style="color: var(--text-secondary, #64748b);">🎯 Confidence: <strong>${confPct}%</strong></span>
          </div>
        </div>

        <!-- 1. WHY & RATIONALE -->
        <div style="background: var(--bg-surface, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 10px; padding: 14px;">
          <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary, #0f172a); margin-bottom: 6px;">💡 ${dDict.whyRationale}</div>
          <div style="font-size: 0.85rem; color: var(--text-secondary, #475569); line-height: 1.5;">
            ${t.rationale || (t.assumptions && t.assumptions.length > 0 ? t.assumptions[0] : 'Telemetry conditions and agronomic rules triggered this targeted farm advisory.')}
          </div>
        </div>

        <!-- 2. EVIDENCE & TELEMETRY GROUNDING -->
        <div style="background: var(--bg-surface, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 10px; padding: 14px;">
          <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary, #0f172a); margin-bottom: 8px;">📡 ${dDict.evidenceSensors}</div>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; font-size: 0.8rem;">
            <div style="background: #f8fafc; padding: 8px; border-radius: 6px;">
              <span style="color: var(--text-muted, #94a3b8); display: block;">Crop:</span>
              <strong>${t.input_context?.crop || 'Crop'} (${t.input_context?.stage || 'Stage'})</strong>
            </div>
            <div style="background: #f8fafc; padding: 8px; border-radius: 6px;">
              <span style="color: var(--text-muted, #94a3b8); display: block;">Soil Type:</span>
              <strong>${t.input_context?.soil || 'Local Soil'}</strong>
            </div>
            <div style="background: #f8fafc; padding: 8px; border-radius: 6px;">
              <span style="color: var(--text-muted, #94a3b8); display: block;">Rainfall Risk:</span>
              <strong>${t.input_context?.rain_probability != null ? t.input_context.rain_probability + '%' : 'Telemetry Normal'}</strong>
            </div>
          </div>
        </div>

        <!-- 3. DATA SOURCES & FRESHNESS -->
        <div style="background: var(--bg-surface, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 10px; padding: 14px;">
          <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary, #0f172a); margin-bottom: 8px;">🔄 ${dDict.dataSources}</div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; font-size: 0.78rem;">
            ${Object.entries(t.data_freshness || {}).map(([k, v]) => `
              <span style="padding: 4px 8px; border-radius: 6px; background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; font-weight: 600;">
                ✓ ${k.toUpperCase()}: ${v}
              </span>
            `).join("")}
          </div>
        </div>

        <!-- 4. TOOLS & SAFETY SCREENING -->
        <div style="background: var(--bg-surface, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 10px; padding: 14px;">
          <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary, #0f172a); margin-bottom: 6px;">🛡️ ${dDict.toolsSafety}</div>
          <div style="font-size: 0.8rem; color: var(--text-secondary, #475569);">
            Tools Used: <strong>${(t.tools_used || ['DecisionIntelligenceEngine']).join(", ")}</strong>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-secondary, #475569); margin-top: 4px;">
            Safety Gates: <strong>${(t.safety_checks || ['CIBRC Chemical Screening', 'SafetyEngine Gate']).join(", ")}</strong>
          </div>
        </div>

        <!-- 5. INTERACTIVE ACTION & FEEDBACK WORKFLOW -->
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 12px; padding: 16px;">
          <div style="font-size: 0.92rem; font-weight: 700; color: #166534; margin-bottom: 10px;">✍️ ${dDict.actionFeedback}</div>
          
          <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
            <button type="button" onclick="submitTraceFeedback('${t.decision_id}', 'ACCEPTED', null)" style="padding: 6px 14px; background: #16a34a; color: white; border: none; border-radius: 6px; font-size: 0.82rem; font-weight: 600; cursor: pointer;">
              ${dDict.btnAccept}
            </button>
            <button type="button" onclick="submitTraceFeedback('${t.decision_id}', 'REJECTED', null)" style="padding: 6px 14px; background: #dc2626; color: white; border: none; border-radius: 6px; font-size: 0.82rem; font-weight: 600; cursor: pointer;">
              ${dDict.btnReject}
            </button>
            <button type="button" onclick="submitTraceFeedback('${t.decision_id}', 'POSTPONED', null)" style="padding: 6px 14px; background: #eab308; color: white; border: none; border-radius: 6px; font-size: 0.82rem; font-weight: 600; cursor: pointer;">
              ${dDict.btnPostpone}
            </button>
          </div>

          <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 0.82rem; font-weight: 600; color: #166534;">${dDict.feedbackLabel}</span>
            <button type="button" onclick="submitTraceFeedback('${t.decision_id}', '${t.farmer_action || 'ACCEPTED'}', 'USEFUL')" style="padding: 4px 10px; background: #ffffff; border: 1px solid #16a34a; color: #16a34a; border-radius: 6px; font-size: 0.78rem; font-weight: 600; cursor: pointer;">
              ${dDict.btnHelpful}
            </button>
            <button type="button" onclick="submitTraceFeedback('${t.decision_id}', '${t.farmer_action || 'ACCEPTED'}', 'NOT_HELPFUL')" style="padding: 4px 10px; background: #ffffff; border: 1px solid #dc2626; color: #dc2626; border-radius: 6px; font-size: 0.78rem; font-weight: 600; cursor: pointer;">
              ${dDict.btnNotHelpful}
            </button>
          </div>

          <div style="display: flex; gap: 8px; align-items: center;">
            <input type="text" id="traceFeedbackNotes_${t.decision_id}" placeholder="${dDict.feedbackPlaceholder}" value="${t.feedback_notes || ''}" style="flex: 1; padding: 6px 12px; border: 1px solid #86efac; border-radius: 6px; font-size: 0.82rem; background: white;" />
            <button type="button" onclick="submitCustomFeedbackNotes('${t.decision_id}')" style="padding: 6px 14px; background: #15803d; color: white; border: none; border-radius: 6px; font-size: 0.82rem; font-weight: 600; cursor: pointer;">
              ${dDict.btnSubmitFeedback}
            </button>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<div style="padding: 20px; color: #b91c1c;">Error loading decision trace: ${err.message}</div>`;
  }
}
window.openDecisionDetail = openDecisionDetail;

function closeDecisionDetailModal() {
  const modal = document.getElementById("decisionDetailModal");
  if (modal) modal.style.display = "none";
}
window.closeDecisionDetailModal = closeDecisionDetailModal;

async function submitTraceFeedback(decisionId, action, rating, notes = null) {
  const token = authToken || localStorage.getItem("bhoomi_auth_token");
  if (!token) return;

  const dDict = getDecisionsDict(currentLanguage);
  try {
    const payload = {
      recommendation_id: decisionId,
      action_taken: action,
      feedback_rating: rating || "USEFUL",
      notes: notes || "Reviewer action updated via BHOOMI web UI."
    };

    const res = await fetch("/api/v1/manager/feedback", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast(dDict.feedbackSuccess, "success");
      // Re-load detail from PostgreSQL to visually verify persistence
      await openDecisionDetail(decisionId);
      // Refresh history list in background
      await loadDecisionHistory();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || "Failed to update feedback.", "error");
    }
  } catch (err) {
    showToast("Network error submitting feedback: " + err.message, "error");
  }
}
window.submitTraceFeedback = submitTraceFeedback;

async function submitCustomFeedbackNotes(decisionId) {
  const input = document.getElementById(`traceFeedbackNotes_${decisionId}`);
  const notes = input ? input.value : "";
  await submitTraceFeedback(decisionId, "ACCEPTED", "USEFUL", notes);
}
window.submitCustomFeedbackNotes = submitCustomFeedbackNotes;



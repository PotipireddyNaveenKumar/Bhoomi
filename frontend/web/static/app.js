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
    ]
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
    ]
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
    ]
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
    ]
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
    ]
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
    ]
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
    ]
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

  populateDistricts("farmerStateInput", "farmerDistrictInput", "Warangal");
  updateUILanguage(currentLanguage);
  initSpeechRecognition();
  initAuth();
});




// ==========================================
// Authentication & Multi-Tenant Isolation
// ==========================================
async function initAuth() {
  const savedUser = localStorage.getItem("bhoomi_current_user");
  const savedToken = localStorage.getItem("bhoomi_auth_token");
  
  // Clean up any legacy manufactured fake tokens
  if (savedToken && savedToken.startsWith("demo_")) {
    localStorage.removeItem("bhoomi_auth_token");
    authToken = null;
  }
  
  if (savedToken && !savedToken.startsWith("demo_") && savedUser) {
    try {
      currentUser = JSON.parse(savedUser);
      authToken = savedToken;
      updateSidebarFarmerProfile(currentUser);
      hideAuthModal();
      loadUserScopedSessions();
      return;
    } catch (e) {
      console.warn("Invalid user storage, prompting login:", e);
    }
  }

  // If reviewer logged in via demo profile without JWT
  if (savedUser) {
    try {
      currentUser = JSON.parse(savedUser);
      authToken = null;
      updateSidebarFarmerProfile(currentUser);
      hideAuthModal();
      loadUserScopedSessions();
      return;
    } catch (e) {}
  }

  // Fresh / incognito reviewer visit: check if backend is running with DEMO_MODE=true
  try {
    const healthRes = await fetch("/health");
    if (healthRes.ok) {
      const healthData = await healthRes.json();
      if (healthData.demo_mode === true) {
        currentUser = {
          id: "demo_farmer_1",
          phone_number: "+919876543210 (Demo Contact)",
          full_name: "Ramesh Kumar (Demo Farmer)",
          preferred_language: currentLanguage || "te",
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
        localStorage.setItem("bhoomi_current_user", JSON.stringify(currentUser));
        updateSidebarFarmerProfile(currentUser);
        hideAuthModal();
        loadUserScopedSessions();
        return;
      }
    }
  } catch (err) {
    console.warn("Error checking demo_mode from /health:", err);
  }

  // Not in DEMO_MODE and not logged in -> Show Authentication Modal
  showAuthModal();
}

function showAuthModal() {
  const modal = document.getElementById("authModal");
  if (modal) modal.style.display = "flex";
  backToOtpStep1();
}

function hideAuthModal() {
  const modal = document.getElementById("authModal");
  if (modal) modal.style.display = "none";
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
    preferred_language: currentLanguage || "te",
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

// Step 1: Send OTP to Mobile Number
async function handleSendOtp() {
  const phoneInput = document.getElementById("otpMobileInput");
  const phone = phoneInput ? phoneInput.value.trim() : "";
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

  try {
    const res = await fetch("/api/v1/auth/send-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone_number: phone })
    });

    const data = await res.json();
    const otpCode = data.otp || data.demo_otp || "1234";

    // Switch to Step 2
    document.getElementById("otpStep1").style.display = "none";
    document.getElementById("otpStep2").style.display = "block";

    const sentBanner = document.getElementById("txtOtpSentInfo");
    if (sentBanner) {
      sentBanner.innerHTML = `📲 SMS sent to +91 ${phone} • (Your OTP is: <b style="color:#10B981; font-size:14px;">${otpCode}</b>)`;
    }

    const otpCodeInput = document.getElementById("otpCodeInput");
    if (otpCodeInput) {
      otpCodeInput.value = ""; // Empty so farmer types the code
      otpCodeInput.placeholder = "Enter 4-digit OTP";
      otpCodeInput.focus();
    }

    // Show farmer detail fields
    const newFields = document.getElementById("newFarmerFields");
    if (newFields) newFields.style.display = "block";

  } catch (e) {
    if (errorMsg) {
      errorMsg.textContent = "Failed to send OTP. Please check your connection.";
      errorMsg.style.display = "block";
    }
  }
}

// Step 2: Verify OTP and Login
async function handleVerifyOtp() {
  const otpInput = document.getElementById("otpCodeInput");
  const otp = otpInput ? otpInput.value.trim() : "";
  const errorMsg = document.getElementById("authErrorMsg");
  if (errorMsg) errorMsg.style.display = "none";

  if (!otp || otp.length < 4) {
    if (errorMsg) {
      errorMsg.textContent = "Please enter the 4-digit OTP code received on your phone.";
      errorMsg.style.display = "block";
    }
    return;
  }


  const name = document.getElementById("farmerNameInput")?.value?.trim() || "Farmer";
  const state = document.getElementById("farmerStateInput")?.value || "Telangana";
  const district = document.getElementById("farmerDistrictInput")?.value?.trim() || "Warangal";
  const crop = document.getElementById("farmerCropInput")?.value?.trim() || "Rice";
  const acres = parseFloat(document.getElementById("farmerAcresInput")?.value || 3.0);
  const soilN = parseFloat(document.getElementById("farmerSoilN")?.value || 90);
  const soilP = parseFloat(document.getElementById("farmerSoilP")?.value || 42);
  const soilK = parseFloat(document.getElementById("farmerSoilK")?.value || 43);
  const soilPh = parseFloat(document.getElementById("farmerSoilPh")?.value || 6.5);

  try {
    const res = await fetch("/api/v1/auth/verify-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone_number: pendingOtpPhone,
        otp: otp,
        full_name: name,
        preferred_language: currentLanguage,
        state: state,
        district: district,
        current_crop: crop,
        land_area_acres: acres,
        soil_n: soilN,
        soil_p: soilP,
        soil_k: soilK,
        soil_ph: soilPh
      })
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("bhoomi_auth_token", authToken);

      currentUser = {
        id: `usr_${pendingOtpPhone}`,
        phone_number: pendingOtpPhone,
        full_name: name,
        preferred_language: currentLanguage,
        state: state,
        district: district,
        land_area_acres: acres,
        current_crop: crop,
        soil_n: soilN,
        soil_p: soilP,
        soil_k: soilK,
        soil_ph: soilPh
      };
      localStorage.setItem("bhoomi_current_user", JSON.stringify(currentUser));
      localStorage.setItem("bhoomi_lang", currentLanguage);

      updateSidebarFarmerProfile(currentUser);
      hideAuthModal();
      updateUILanguage(currentLanguage);
      loadUserScopedSessions();
    } else {
      const err = await res.json().catch(() => ({}));
      let msg = "Invalid OTP code entered. Please try again.";
      if (typeof err.detail === "string") {
        msg = err.detail;
      } else if (Array.isArray(err.detail)) {
        msg = err.detail.map(d => d.msg || JSON.stringify(d)).join("; ");
      } else if (err.error && err.error.message) {
        msg = err.error.message;
      } else if (err.message) {
        msg = err.message;
      }
      if (errorMsg) {
        errorMsg.textContent = msg;
        errorMsg.style.display = "block";
      }
    }
  } catch (e) {
    if (errorMsg) {
      errorMsg.textContent = "Server error verifying OTP: " + (e.message || "Please try again.");
      errorMsg.style.display = "block";
    }
  }
}


function backToOtpStep1() {
  const step1 = document.getElementById("otpStep1");
  const step2 = document.getElementById("otpStep2");
  const errorMsg = document.getElementById("authErrorMsg");
  if (step1) step1.style.display = "block";
  if (step2) step2.style.display = "none";
  if (errorMsg) errorMsg.style.display = "none";
}


function handleLogout() {
  if (confirm("మీరు ఖచ్చితంగా లాగ్ అవుట్ చేయాలనుకుంటున్నారా? (Are you sure you want to log out?)")) {
    localStorage.removeItem("bhoomi_auth_token");
    localStorage.removeItem("bhoomi_current_user");
    authToken = null;
    currentUser = null;
    closeProfileModal();
    sessionsList = [];
    renderSessionList();
    showAuthModal();
  }
}

function updateSidebarFarmerProfile(user) {
  const nameEl = document.getElementById("sidebarFarmerName");
  const farmEl = document.getElementById("sidebarFarmerFarm");
  if (nameEl) nameEl.textContent = user.full_name || "Farmer";
  if (farmEl) {
    const district = user.district || "Warangal";
    const state = user.state || "Telangana";
    const acres = user.land_area_acres || 3.0;
    const crop = user.current_crop || "Rice";
    farmEl.textContent = `${district}, ${state} • ${acres} Acres (${crop})`;
  }
}

// ==========================================
// Regional State & Districts Mapping
// ==========================================
const STATE_DISTRICTS = {
  "Telangana": [
    "Warangal", "Karimnagar", "Nalgonda", "Khammam", "Nizamabad",
    "Mahabubnagar", "Medak", "Rangareddy", "Adilabad", "Suryapet",
    "Siddipet", "Jagtial", "Kamareddy", "Peddapalli", "Mancherial"
  ],
  "Andhra Pradesh": [
    "Guntur", "Krishna", "East Godavari", "West Godavari", "Kurnool",
    "Anantapur", "Vizianagaram", "Visakhapatnam", "Chittoor", "Prakasam",
    "YSR Kadapa", "Nellore", "Srikakulam", "Eluru", "Kakinada"
  ],
  "Maharashtra": [
    "Pune", "Nagpur", "Nashik", "Chhatrapati Sambhajinagar (Aurangabad)", "Solapur",
    "Kolhapur", "Amravati", "Yavatmal", "Ahmednagar", "Satara",
    "Jalgaon", "Nanded", "Latur", "Buldhana", "Akola"
  ],
  "Karnataka": [
    "Belagavi", "Mysuru", "Mandya", "Dharwad", "Ballari",
    "Raichur", "Davanagere", "Shivamogga", "Tumakuru", "Hassan",
    "Kalaburagi", "Vijayapura", "Bagalkot", "Chikkamagaluru", "Udupi"
  ],
  "Tamil Nadu": [
    "Thanjavur", "Madurai", "Coimbatore", "Salem", "Tiruchirappalli",
    "Erode", "Tirunelveli", "Vellore", "Dindigul", "Cuddalore",
    "Tiruppur", "Kanchipuram", "Thiruvarur", "Nagapattinam", "Theni"
  ],
  "Punjab": [
    "Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda",
    "Firozpur", "Sangrur", "Hoshiarpur", "Moga", "Gurdaspur",
    "Faridkot", "Fazilka", "Kapurthala", "Mansa", "Muktsar"
  ]
};

function populateDistricts(stateSelectId, districtSelectId, selectedDistrict = null) {
  const stateEl = document.getElementById(stateSelectId);
  const distEl = document.getElementById(districtSelectId);
  if (!stateEl || !distEl) return;

  const stateVal = stateEl.value || "Telangana";
  const districts = STATE_DISTRICTS[stateVal] || STATE_DISTRICTS["Telangana"];

  distEl.innerHTML = "";
  districts.forEach(d => {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = d;
    distEl.appendChild(opt);
  });

  if (selectedDistrict && districts.includes(selectedDistrict)) {
    distEl.value = selectedDistrict;
  } else if (selectedDistrict) {
    const customOpt = document.createElement("option");
    customOpt.value = selectedDistrict;
    customOpt.textContent = selectedDistrict;
    distEl.appendChild(customOpt);
    distEl.value = selectedDistrict;
  } else {
    distEl.value = districts[0];
  }
}

// ==========================================
// Farmer Profile Edit Modal
// ==========================================
function openProfileModal() {
  const modal = document.getElementById("profileModal");
  if (!modal) return;

  const u = currentUser || { full_name: "Ramesh Rao", state: "Telangana", district: "Warangal", land_area_acres: 3.0, current_crop: "Rice", soil_n: 90, soil_p: 42, soil_k: 43, soil_ph: 6.5 };

  document.getElementById("profName").value = u.full_name || "";
  document.getElementById("profState").value = u.state || "Telangana";
  
  populateDistricts("profState", "profDistrict", u.district || "Warangal");

  const profCropEl = document.getElementById("profCrop");
  if (profCropEl) {
    if (u.current_crop && ![...profCropEl.options].some(o => o.value === u.current_crop)) {
      const opt = new Option(u.current_crop, u.current_crop, true, true);
      profCropEl.add(opt);
    }
    profCropEl.value = u.current_crop || "Rice";
  }

  document.getElementById("profAcres").value = u.land_area_acres || 3.0;
  document.getElementById("profSoilN").value = u.soil_n || 90;
  document.getElementById("profSoilP").value = u.soil_p || 42;
  document.getElementById("profSoilK").value = u.soil_k || 43;
  document.getElementById("profSoilPh").value = u.soil_ph || 6.5;

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
        const tot = data.expected_total_production_quintals || (ypa * (data.area_acres || 3.0));
        const conf = data.confidence_interval_95;
        let rangeHtml = "";
        if (Array.isArray(conf) && conf.length === 2) {
          rangeHtml = `<div class="metric-pill">95% CI: <strong>${Number(conf[0]).toFixed(1)} - ${Number(conf[1]).toFixed(1)} Qtl</strong></div>`;
        }
        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">📈 ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">
              <div class="metric-pill highlight">Expected Yield: <strong>${Number(ypa).toFixed(1)} Qtl/Acre</strong></div>
              <div class="metric-pill">Total Est. Production: <strong>${Number(tot).toFixed(1)} Qtl</strong></div>
              ${rangeHtml}
            </div>
          </div>
        `);
      }

      // 3. Mandi Market Realization Card
      else if (type === "market_card") {
        const recMandi = data.recommended_mandi || "Regional Mandi";
        const netReal = data.best_net_realization || data.net_realization || 0;
        const modal = data.benchmark_modal_price || data.modal_price || 0;
        const trend = data.price_trend || "";
        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">🏪 ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">
              <div class="metric-pill highlight">Best Mandi: <strong>${escapeHtml(recMandi)}</strong></div>
              ${modal ? `<div class="metric-pill">Modal Price: <strong>₹${Number(modal).toLocaleString('en-IN')}/Qtl</strong></div>` : ''}
              <div class="metric-pill highlight">Net Realization: <strong>₹${Number(netReal).toLocaleString('en-IN')}/Qtl</strong></div>
              ${trend ? `<div class="metric-pill">Trend: <strong>${escapeHtml(trend)}</strong></div>` : ''}
            </div>
          </div>
        `);
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
        const temp = cur.temperature_celsius || 31.5;
        const cond = cur.condition || "Partly Cloudy";
        const rain = cur.precipitation_probability !== undefined ? cur.precipitation_probability : 40;
        const hum = cur.humidity_percent || 65;
        const wind = cur.wind_speed_kmh || 12;
        cardsHtml.push(`
          <div class="assistant-card">
            <div class="card-title">🌦️ ${escapeHtml(title)}</div>
            <div class="metrics-pill-grid">
              <div class="metric-pill highlight">Temp: <strong>${temp}°C (${escapeHtml(cond)})</strong></div>
              <div class="metric-pill">Rain Chance: <strong>${rain}%</strong></div>
              <div class="metric-pill">Humidity: <strong>${hum}%</strong></div>
              <div class="metric-pill">Wind: <strong>${wind} km/h</strong></div>
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
      if (!cropHint && currentUser && currentUser.active_crop) {
        cropHint = cropMap[currentUser.active_crop.toLowerCase()] || "";
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


function initVoiceCallRecognizer() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRec) {
    voiceCallRecognizer = new SpeechRec();
    voiceCallRecognizer.continuous = true;
    voiceCallRecognizer.interimResults = true;

    voiceCallRecognizer.onstart = () => {
      setVoiceOrbState("listening");
      const farmerSubtitle = document.getElementById("voiceFarmerText");
      if (farmerSubtitle) {
        farmerSubtitle.textContent = currentLanguage === "te" ? "వింటున్నాను... మీ సమస్యను పూర్తిగా మాట్లాడండి..." : (currentLanguage === "hi" ? "सुन रहे हैं... अपनी पूरी समस्या बताएं..." : "Listening carefully... Explain your full problem...");
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
        const farmerSubtitle = document.getElementById("voiceFarmerText");
        if (farmerSubtitle) {
          farmerSubtitle.innerHTML = `<span style="color:var(--accent-rose);">⚠️ Microphone blocked. <a href="javascript:void(0)" onclick="openMicPermissionModal()" style="color:var(--accent-emerald); text-decoration:underline; font-weight:600;">Click to Enable Permission</a></span>`;
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
  isVoiceCallOpen = true;
  isVoiceCallActiveMic = true;
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

  updateVoiceModalLabels();
  startVoiceCallListening();
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
    const farmerSubtitle = document.getElementById("voiceFarmerText");
    if (farmerSubtitle) {
      farmerSubtitle.textContent = currentLanguage === "te" ? "వింటున్నాను... మీ ప్రశ్నను మాట్లాడండి..." : "Listening... Speak your question clearly...";
    }
  } catch (err) {
    console.error("[VOICE_CALL] Mic access error:", err);
    isVoiceCallActiveMic = false;
    setVoiceOrbState("idle");
    const farmerSubtitle = document.getElementById("voiceFarmerText");
    if (farmerSubtitle) {
      farmerSubtitle.innerHTML = `<span style="color:var(--accent-rose,#ef4444); font-size:0.92rem;">⚠️ Microphone not accessible (${err.name || 'Notice'}). <a href="javascript:void(0)" onclick="openMicPermissionModal()" style="color:var(--accent-emerald,#10b981); text-decoration:underline; font-weight:600; margin-left:6px;">Tap for Permission Help & Quick Prompts</a></span>`;
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
  const aiSubtitle = document.getElementById("voiceAiText");
  if (aiSubtitle) {
    aiSubtitle.textContent = currentLanguage === "te" ? "సమగ్ర వ్యవసాయ విశ్లేషణ సిద్ధం చేస్తున్నాము..." : (currentLanguage === "hi" ? "विश्लेषण कर रहे हैं..." : "Gathering farm data and analyzing...");
  }

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
  const aiSubtitle = document.getElementById("voiceAiText");
  if (aiSubtitle) {
    aiSubtitle.textContent = currentLanguage === "te" ? "సమగ్ర వ్యవసాయ విశ్లేషణ సిద్ధం చేస్తున్నాము..." : "Gathering farm data and analyzing...";
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
    }
    if (aiSubtitle) {
      aiSubtitle.textContent = replyText;
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
      aiSubtitle.innerHTML = `${replyText}<br><button onclick="playVoiceCallAssistantResponse('${audioBase64}', '')" style="margin-top:10px;padding:8px 16px;border-radius:20px;background:var(--accent,#2e7d32);color:#fff;border:none;cursor:pointer;font-weight:600;">🔊 Tap to Listen to Spoken Answer</button>`;
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
  const langCodes = { te: "te-IN", hi: "hi-IN", en: "en-IN", ta: "ta-IN", kn: "kn-IN", mr: "mr-IN" };
  utterance.lang = langCodes[currentLanguage] || "te-IN";
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
  const orb = document.getElementById("voiceOrb");
  const badge = document.getElementById("voiceStatusBadge");
  const micBtn = document.getElementById("btnVoiceCallMic");
  const micLabel = document.getElementById("voiceCallMicLabel");
  const orbIcon = document.getElementById("orbIcon");

  if (!orb) return;
  orb.className = `voice-orb ${state}`;

  if (state === "listening") {
    if (orbIcon) orbIcon.textContent = "🎙️";
    if (badge) badge.textContent = currentLanguage === "te" ? "పూర్తిగా మాట్లాడండి, వింటున్నాను... (Listening...)" : (currentLanguage === "hi" ? "पूरी बात बताएं, सुन रहे हैं..." : "Listening carefully...");
    if (micBtn) micBtn.className = "btn-voice-action mic recording";
    if (micLabel) micLabel.textContent = currentLanguage === "te" ? "వింటున్నాను..." : (currentLanguage === "hi" ? "सुन रहे हैं..." : "Listening...");
  } else if (state === "thinking") {
    if (orbIcon) orbIcon.textContent = "🧠";
    if (badge) badge.textContent = currentLanguage === "te" ? "విశ్లేషిస్తున్నాను... (Analyzing...)" : (currentLanguage === "hi" ? "विश्लेषण कर रहे हैं..." : "Analyzing...");
    if (micBtn) micBtn.className = "btn-voice-action mic";
    if (micLabel) micLabel.textContent = currentLanguage === "te" ? "ఆలోచిస్తున్నాను..." : "Thinking...";
  } else if (state === "speaking") {
    if (orbIcon) orbIcon.textContent = "🗣️";
    if (badge) badge.textContent = currentLanguage === "te" ? "సమాధానం ఇస్తున్నాను... (Speaking...)" : (currentLanguage === "hi" ? "उत्तर दे रहे हैं..." : "Speaking...");
    if (micBtn) micBtn.className = "btn-voice-action mic";
    if (micLabel) micLabel.textContent = currentLanguage === "te" ? "సమాధానం ఇస్తున్నాను..." : "Speaking...";
  } else {
    if (orbIcon) orbIcon.textContent = "🎙️";
    if (badge) badge.textContent = currentLanguage === "te" ? "మాట్లాడటానికి నొక్కండి (Tap to Speak)" : "Tap to Speak";
    if (micBtn) micBtn.className = "btn-voice-action mic";
    if (micLabel) micLabel.textContent = currentLanguage === "te" ? "మాట్లాడండి (Speak)" : "Speak";
  }
}

function updateVoiceModalLabels() {
  const title = document.getElementById("voiceCallAgentTitle");
  const endCall = document.getElementById("txtEndCall");
  const btnHeader = document.getElementById("txtVoiceCallBtn");
  const aiRole = document.getElementById("voiceAiRole");

  if (title) title.textContent = "BHOOMI Voice Assistant";
  if (aiRole) aiRole.textContent = "🌾 BHOOMI (Voice Assistant):";

  if (currentLanguage === "te") {
    if (endCall) endCall.textContent = "ముగించు (End)";
    if (btnHeader) btnHeader.textContent = "Live Voice Call";
  } else if (currentLanguage === "hi") {
    if (endCall) endCall.textContent = "समाप्त करें (End)";
    if (btnHeader) btnHeader.textContent = "Live Voice Call";
  } else {
    if (endCall) endCall.textContent = "End Call";
    if (btnHeader) btnHeader.textContent = "Live Voice Call";
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
window.handleVerifyOtp = handleVerifyOtp;
window.backToOtpStep1 = backToOtpStep1;
window.onAuthLanguageChanged = onAuthLanguageChanged;
window.onLanguageChanged = onLanguageChanged;
window.sendMessage = sendMessage;
window.sendQuickQuery = sendQuickQuery;
window.removeAttachedImage = removeAttachedImage;
window.analyzeSampleLeaf = analyzeSampleLeaf;




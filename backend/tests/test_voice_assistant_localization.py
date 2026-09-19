import re
import pytest
from pathlib import Path
from html.parser import HTMLParser

VOID_ELEMENTS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

class TagExtractor(HTMLParser):
    def __init__(self, target_id):
        super().__init__()
        self.target_id = target_id
        self.in_target = False
        self.target_tags = 0
        self.text_chunks = []
        self.found = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if attrs_dict.get("id") == self.target_id:
            self.in_target = True
            self.found = True
            self.target_tags = 1
        elif self.in_target:
            if tag.lower() not in VOID_ELEMENTS:
                self.target_tags += 1

    def handle_endtag(self, tag):
        if self.in_target:
            if tag.lower() not in VOID_ELEMENTS:
                self.target_tags -= 1
                if self.target_tags == 0:
                    self.in_target = False

    def handle_data(self, data):
        if self.in_target:
            self.text_chunks.append(data)

def extract_text_by_id(html_content, elem_id):
    parser = TagExtractor(elem_id)
    parser.feed(html_content)
    return parser.found, "".join(parser.text_chunks)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
INDEX_HTML = ROOT_DIR / "frontend" / "web" / "index.html"
APP_JS = ROOT_DIR / "frontend" / "web" / "static" / "app.js"

TELUGU_CHAR_RANGE = re.compile(r'[\u0C00-\u0C7F]')

SUPPORTED_LANGUAGES = ["en", "te", "hi", "ta", "kn", "mr", "ml"]

REQUIRED_VOICE_KEYS = [
    "agentTitle", "farmerRole", "farmerInitialText", "farmerListening",
    "aiRole", "aiGreeting", "statusListening", "statusThinking",
    "statusSpeaking", "statusIdle", "micListening", "micThinking",
    "micSpeaking", "micTapToSpeak", "endCall", "micError",
    "tapForHelp", "tapToListen"
]

def test_index_html_voice_modal_zero_telugu_default():
    """
    TEST 1: In English default mode, #voiceCallModal in index.html must have ZERO Telugu characters.
    """
    assert INDEX_HTML.exists(), "index.html must exist"
    html_content = INDEX_HTML.read_text(encoding="utf-8")
    
    found, modal_text = extract_text_by_id(html_content, "voiceCallModal")
    assert found, "#voiceCallModal must exist in index.html"
    
    telugu_matches = TELUGU_CHAR_RANGE.findall(modal_text)
    assert len(telugu_matches) == 0, f"Found unexpected Telugu characters in default #voiceCallModal: {set(telugu_matches)}"


def test_index_html_voice_modal_elements_exist_and_english():
    """
    TEST 2: Verify all key voice modal elements exist with proper IDs and canonical English defaults.
    """
    html_content = INDEX_HTML.read_text(encoding="utf-8")
    
    # Title
    found_title, title_text = extract_text_by_id(html_content, "voiceCallAgentTitle")
    assert found_title, "#voiceCallAgentTitle must exist"
    assert "BHOOMI Voice Assistant" in title_text
    
    # Status Badge
    found_badge, badge_text = extract_text_by_id(html_content, "voiceStatusBadge")
    assert found_badge, "#voiceStatusBadge must exist"
    assert "Listening carefully..." in badge_text
    assert len(TELUGU_CHAR_RANGE.findall(badge_text)) == 0
    
    # Farmer Role & Text
    found_farmer_role, role_text = extract_text_by_id(html_content, "voiceFarmerRole")
    assert found_farmer_role, "#voiceFarmerRole must exist"
    assert "Farmer" in role_text
    assert len(TELUGU_CHAR_RANGE.findall(role_text)) == 0
    
    found_farmer_text, text_text = extract_text_by_id(html_content, "voiceFarmerText")
    assert found_farmer_text, "#voiceFarmerText must exist"
    assert "Speak your question" in text_text
    assert len(TELUGU_CHAR_RANGE.findall(text_text)) == 0
    
    # AI Role & Text
    found_ai_role, ai_role_text = extract_text_by_id(html_content, "voiceAiRole")
    assert found_ai_role, "#voiceAiRole must exist"
    assert "BHOOMI" in ai_role_text
    assert len(TELUGU_CHAR_RANGE.findall(ai_role_text)) == 0
    
    found_ai_text, ai_text = extract_text_by_id(html_content, "voiceAiText")
    assert found_ai_text, "#voiceAiText must exist"
    assert "Hello!" in ai_text
    assert len(TELUGU_CHAR_RANGE.findall(ai_text)) == 0
    
    # Mic button label
    found_mic, mic_text = extract_text_by_id(html_content, "voiceCallMicLabel")
    assert found_mic, "#voiceCallMicLabel must exist"
    assert "Tap to Speak" in mic_text
    assert len(TELUGU_CHAR_RANGE.findall(mic_text)) == 0
    
    # End Call button
    found_end, end_text = extract_text_by_id(html_content, "txtEndCall")
    assert found_end, "#txtEndCall must exist"
    assert "End Call" in end_text
    assert len(TELUGU_CHAR_RANGE.findall(end_text)) == 0


def test_app_js_i18n_voice_dictionaries_all_supported_languages():
    """
    TEST 3: Verify that I18N in app.js contains a complete voice block for all 7 supported languages.
    """
    assert APP_JS.exists(), "app.js must exist"
    js_content = APP_JS.read_text(encoding="utf-8")
    
    for lang in SUPPORTED_LANGUAGES:
        pattern = rf'{lang}:\s*\{{.*?voice:\s*\{{'
        assert re.search(pattern, js_content, re.DOTALL), f"Language '{lang}' missing voice block in I18N"


def test_app_js_english_voice_zero_telugu_characters():
    """
    TEST 4: In app.js, the English voice dictionary (I18N.en.voice) MUST NOT contain any Telugu characters.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    
    # Extract en voice block
    en_match = re.search(r'en:\s*\{.*?(voice:\s*\{.*?\}\n\s*\})', js_content, re.DOTALL)
    assert en_match is not None, "Could not extract I18N.en.voice"
    en_voice_str = en_match.group(1)
    
    telugu_matches = TELUGU_CHAR_RANGE.findall(en_voice_str)
    assert len(telugu_matches) == 0, f"Found Telugu Unicode characters in I18N.en.voice: {set(telugu_matches)}"
    
    # Check all required keys exist in en
    for key in REQUIRED_VOICE_KEYS:
        assert f"{key}:" in en_voice_str, f"Missing key '{key}' in I18N.en.voice"


def test_app_js_telugu_voice_contains_proper_telugu_terminology():
    """
    TEST 5: In app.js, I18N.te.voice contains authentic, approved Telugu translations.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    te_match = re.search(r'te:\s*\{.*?(voice:\s*\{.*?\}\n\s*\})', js_content, re.DOTALL)
    assert te_match is not None, "Could not extract I18N.te.voice"
    te_voice_str = te_match.group(1)
    
    expected_terms = [
        "భూమి వాయిస్ అసిస్టెంట్",
        "రైతు",
        "నమస్కారం రైతు మిత్రమా!",
        "వింటున్నాను",
        "సమగ్ర వ్యవసాయ విశ్లేషణ",
        "ముగించు"
    ]
    for term in expected_terms:
        assert term in te_voice_str, f"Expected Telugu term '{term}' missing in I18N.te.voice"
        
    for key in REQUIRED_VOICE_KEYS:
        assert f"{key}:" in te_voice_str, f"Missing key '{key}' in I18N.te.voice"


def test_app_js_non_telugu_languages_zero_telugu_characters():
    """
    TEST 6: Verify Hindi, Tamil, Kannada, Marathi, Malayalam voice dictionaries have zero Telugu characters.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    for lang in ["hi", "ta", "kn", "mr", "ml"]:
        match = re.search(rf'{lang}:\s*\{{.*?(voice:\s*\{{.*?\}}\n\s*\}})', js_content, re.DOTALL)
        assert match is not None, f"Could not extract I18N.{lang}.voice"
        block = match.group(1)
        telugu_matches = TELUGU_CHAR_RANGE.findall(block)
        assert len(telugu_matches) == 0, f"Found unexpected Telugu characters in I18N.{lang}.voice: {set(telugu_matches)}"


def test_app_js_get_voice_dict_fallback_strictly_english():
    """
    TEST 7: Verify getVoiceDict fallback strategy:
    If a language or key is missing, fallback is strictly English (I18N.en.voice), NEVER Telugu.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    assert "function getVoiceDict(lang)" in js_content
    assert "const english = (I18N.en && I18N.en.voice) ? I18N.en.voice : {};" in js_content
    assert "if (!current) return english;" in js_content
    assert "Object.assign({}, english, current)" in js_content


def test_app_js_get_locale_for_lang_mapping():
    """
    TEST 8: Verify getLocaleForLang returns correct BCP-47 locale tags for Indian languages.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    assert "function getLocaleForLang(lang)" in js_content
    assert 'en: "en-IN"' in js_content
    assert 'te: "te-IN"' in js_content
    assert 'hi: "hi-IN"' in js_content
    assert 'ta: "ta-IN"' in js_content
    assert 'kn: "kn-IN"' in js_content
    assert 'mr: "mr-IN"' in js_content
    assert 'ml: "ml-IN"' in js_content
    assert 'return map[lang] || "en-IN";' in js_content


def test_app_js_fallback_voice_call_speech_no_telugu_default():
    """
    TEST 9: In fallbackVoiceCallSpeech(), ensure default speech synthesis language
    uses getLocaleForLang(currentLanguage) rather than hardcoded te-IN.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    assert 'utterance.lang = getLocaleForLang(currentLanguage);' in js_content
    # Ensure || "te-IN" is NOT in fallbackVoiceCallSpeech
    speech_match = re.search(r'function fallbackVoiceCallSpeech\(text\)\s*\{(.*?)\}', js_content, re.DOTALL)
    assert speech_match is not None
    speech_body = speech_match.group(1)
    assert '|| "te-IN"' not in speech_body


def test_app_js_update_voice_modal_labels_synchronizes_recognizer_and_dom():
    """
    TEST 10: Verify updateVoiceModalLabels updates all DOM elements, recognizers, and orb state.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    assert "function updateVoiceModalLabels(lang = currentLanguage)" in js_content
    assert 'document.getElementById("voiceCallAgentTitle")' in js_content
    assert 'document.getElementById("voiceFarmerRole")' in js_content
    assert 'document.getElementById("voiceAiRole")' in js_content
    assert 'document.getElementById("txtEndCall")' in js_content
    assert 'document.getElementById("voiceFarmerText")' in js_content
    assert 'document.getElementById("voiceAiText")' in js_content
    assert "setVoiceOrbState(currentVoiceOrbState || \"idle\");" in js_content
    assert "voiceCallRecognizer.lang = localeTag;" in js_content
    assert "speechRecognizer.lang = localeTag;" in js_content


def test_app_js_global_language_change_lifecycle():
    """
    TEST 11: Verify onLanguageChanged triggers updateUILanguage which calls updateVoiceModalLabels.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    assert "function onLanguageChanged(lang)" in js_content
    assert "updateVoiceModalLabels(" in js_content
    assert "updateFinanceModalLanguage(lang);" in js_content


@pytest.mark.asyncio
async def test_backend_voice_endpoints_support_multilingual():
    """
    TEST 12: Verify backend voice router accepts language parameters and defaults to en.
    """
    from app.api.v1.voice import FALLBACK_PROMPTS
    for lang in ["en", "te", "hi", "ta", "kn", "ml"]:
        assert lang in FALLBACK_PROMPTS, f"Backend FALLBACK_PROMPTS missing language {lang}"
    assert FALLBACK_PROMPTS["en"].startswith("Hello")
    assert "నమస్కారం" in FALLBACK_PROMPTS["te"]
    assert "नमस्ते" in FALLBACK_PROMPTS["hi"]

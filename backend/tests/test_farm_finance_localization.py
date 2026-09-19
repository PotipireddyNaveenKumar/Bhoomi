import re
import json
import pytest
from pathlib import Path
from decimal import Decimal
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



from app.services.finance.profit_service import FinancialService
from app.schemas.finance import ProfitCalculationRequest
from app.services.simulation.simulation_service import SimulationService
from app.schemas.simulation import SimulationRequest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
INDEX_HTML = ROOT_DIR / "frontend" / "web" / "index.html"
APP_JS = ROOT_DIR / "frontend" / "web" / "static" / "app.js"

TELUGU_CHAR_RANGE = re.compile(r'[\u0C00-\u0C7F]')

def test_index_html_finance_modal_zero_telugu_default():
    """
    TEST 1: In English default mode, #financeModal in index.html must have ZERO Telugu characters.
    """
    assert INDEX_HTML.exists(), "index.html must exist"
    html_content = INDEX_HTML.read_text(encoding="utf-8")
    
    found, modal_text = extract_text_by_id(html_content, "financeModal")
    assert found, "#financeModal must exist in index.html"
    
    telugu_matches = TELUGU_CHAR_RANGE.findall(modal_text)
    assert len(telugu_matches) == 0, f"Found unexpected Telugu characters in default #financeModal: {set(telugu_matches)}"
    
    # Check title and subtitle are canonical English
    found_title, title_text = extract_text_by_id(html_content, "txtFinanceModalTitle")
    assert found_title
    assert "Farm Finance & Profit" in title_text
    
    found_sub, sub_text = extract_text_by_id(html_content, "txtFinanceModalSub")
    assert found_sub
    assert "7-Component Cost Breakdown" in sub_text


def test_index_html_header_finance_button_zero_telugu():
    """
    Verify the header button opening Farm Finance has zero Telugu in default HTML.
    """
    html_content = INDEX_HTML.read_text(encoding="utf-8")
    found_btn, btn_text = extract_text_by_id(html_content, "btnOpenFinance")
    assert found_btn
    assert "Finance & Profit" in btn_text
    assert len(TELUGU_CHAR_RANGE.findall(btn_text)) == 0



def test_app_js_i18n_finance_dictionaries_all_supported_languages():
    """
    Verify that I18N in app.js contains complete finance dictionaries for:
    en, te, hi, ta, kn, mr, ml.
    """
    assert APP_JS.exists(), "app.js must exist"
    js_content = APP_JS.read_text(encoding="utf-8")
    
    for lang in ["en", "te", "hi", "ta", "kn", "mr", "ml"]:
        pattern = rf'{lang}:\s*\{{.*?chips:\s*\[.*?finance:\s*\{{'
        assert re.search(pattern, js_content, re.DOTALL), f"Language '{lang}' missing finance block in I18N"



def test_app_js_english_finance_zero_telugu_characters():
    """
    TEST 1 & 10: In app.js, the English finance dictionary (I18N.en.finance) MUST NOT contain any Telugu characters.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    
    # Extract en block
    en_match = re.search(r'en:\s*\{.*?(finance:\s*\{.*?\}\n\s*\})', js_content, re.DOTALL)
    assert en_match is not None, "Could not extract I18N.en.finance"
    en_finance_str = en_match.group(1)
    
    telugu_matches = TELUGU_CHAR_RANGE.findall(en_finance_str)
    assert len(telugu_matches) == 0, f"Found Telugu Unicode characters in I18N.en.finance: {set(telugu_matches)}"


def test_app_js_telugu_finance_contains_proper_telugu_terminology():
    """
    TEST 2: In app.js, I18N.te.finance contains authentic, approved Telugu translations.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    te_match = re.search(r'te:\s*\{.*?(finance:\s*\{.*?\}\n\s*\})', js_content, re.DOTALL)
    assert te_match is not None, "Could not extract I18N.te.finance"
    te_finance_str = te_match.group(1)
    
    # Verify expected Telugu terminology
    expected_terms = [
        "వ్యవసాయ ఆర్థిక విశ్లేషణ & లాభం",
        "విత్తనాలు",
        "ఎరువులు",
        "పురుగుమందులు",
        "కూలి ఖర్చులు",
        "నీటిపారుదల",
        "ట్రాక్టర్/యంత్రాలు",
        "ఇతర ఖర్చులు",
        "బ్రేక్-ఈవెన్",
        "లాభం & ఖర్చులు లెక్కించండి"
    ]
    for term in expected_terms:
        assert term in te_finance_str, f"Expected Telugu term '{term}' missing in I18N.te.finance"


def test_app_js_hindi_and_other_languages_zero_telugu_characters():
    """
    TEST 5: Verify Hindi, Tamil, Kannada, Marathi, Malayalam dictionaries have zero Telugu characters.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    for lang in ["hi", "ta", "kn", "mr", "ml"]:
        match = re.search(rf'{lang}:\s*\{{.*?(finance:\s*\{{.*?\}}\n\s*\}})', js_content, re.DOTALL)
        assert match is not None, f"Could not extract I18N.{lang}.finance"
        block = match.group(1)
        telugu_matches = TELUGU_CHAR_RANGE.findall(block)
        assert len(telugu_matches) == 0, f"Found unexpected Telugu characters in I18N.{lang}.finance: {set(telugu_matches)}"


def test_app_js_architecture_fallback_to_english_not_telugu():
    """
    TEST 9: Verify getFinanceDict fallback strategy:
    If a language or key is missing, fallback is strictly English (I18N.en.finance), NEVER Telugu.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    assert "function getFinanceDict(lang)" in js_content
    assert "const english = (I18N.en && I18N.en.finance) ? I18N.en.finance : {};" in js_content
    assert "if (!current) return english;" in js_content
    # Ensure there is NO fallback to 'te'
    assert '|| I18N.te.finance' not in js_content
    assert '|| "te"' not in js_content


def test_app_js_single_authoritative_locale_lifecycle():
    """
    TEST 3, 4, 6, 7: Verify single global locale architecture.
    1. currentLanguage is initialized from localStorage or 'en'.
    2. onLanguageChanged updates currentLanguage, localStorage, syncs selectors, and calls updateUILanguage(lang).
    3. updateUILanguage(lang) calls updateFinanceModalLanguage(lang).
    4. openFinanceModal() calls updateFinanceModalLanguage(currentLanguage).
    5. No split-brain state exists.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    
    assert "let currentLanguage = localStorage.getItem(\"bhoomi_lang\") || \"en\";" in js_content
    assert "function onLanguageChanged(lang)" in js_content
    assert "updateFinanceModalLanguage(lang);" in js_content
    assert "updateFinanceModalLanguage(currentLanguage);" in js_content


def test_app_js_dynamic_results_immediate_rerender_on_language_change():
    """
    Verify that updateFinanceModalLanguage re-renders cached simulation or finance results
    immediately when language changes without requiring the user to recalculate or reload.
    """
    js_content = APP_JS.read_text(encoding="utf-8")
    assert "window._lastFinanceData = data;" in js_content
    assert "window._lastSimulationData = data;" in js_content
    assert "if (window._lastActiveFinanceTab === 'sim' && window._lastSimulationData)" in js_content
    assert "renderSimulationResults(window._lastSimulationData);" in js_content
    assert "renderFinanceResults(window._lastFinanceData);" in js_content


def test_backend_deterministic_calculations_intact():
    """
    TEST 19: Confirm deterministic calculations, cost formulas, and What-If simulation
    remain 100% intact and unchanged.
    10 quintals * 12,000 = 1,20,000 revenue
    1,20,000 - 70,000 = 50,000 net profit
    """
    req = ProfitCalculationRequest(
        crop_name="Chilli",
        area_acres=Decimal("1.0"),
        expected_yield_quintals_per_acre=Decimal("10.0"),
        expected_market_price_per_quintal=Decimal("12000.00"),
        cultivation_cost_total=Decimal("70000.00")
    )
    res = FinancialService.calculate_profit(req)
    assert res.total_production_quintals == Decimal("10.00")
    assert res.gross_revenue == Decimal("120000.00")
    assert res.net_profit == Decimal("50000.00")
    assert res.profit_per_acre == Decimal("50000.00")
    assert res.return_on_investment_percent == Decimal("71.43")

    sim_req = SimulationRequest(
        crop_name="Chilli",
        area_acres=Decimal("1.0"),
        baseline_yield_quintals_per_acre=Decimal("10.0"),
        baseline_market_price_per_quintal=Decimal("12000.00"),
        baseline_cultivation_cost=Decimal("70000.00"),
        price_change_percent=Decimal("-20.0"),
        yield_change_percent=Decimal("0.0"),
        cost_change_percent=Decimal("0.0"),
        rainfall_change_percent=Decimal("0.0"),
    )
    sim_res = SimulationService.run_simulation(sim_req)
    assert sim_res.baseline.net_profit == Decimal("50000.00")
    assert sim_res.simulated_scenario.price_per_quintal == Decimal("9600.00")
    assert sim_res.simulated_scenario.net_profit == Decimal("26000.00")
    assert sim_res.simulated_scenario.profit_difference == Decimal("-24000.00")

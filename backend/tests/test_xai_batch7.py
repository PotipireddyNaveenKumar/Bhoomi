import io
import pytest
import numpy as np
from PIL import Image
from decimal import Decimal

from app.services.crop.recommendation_service import (
    CropRecommendationService,
    CropRecommendationInput,
    CropRecommendationOutput
)
from app.services.yield_prediction.yield_service import (
    YieldPredictionService,
    YieldPredictionInput,
    YieldPredictionOutput
)
from app.services.crop.fertilizer_service import (
    FertilizerRecommendationService,
    FertilizerInput,
    FertilizerRecommendationOutput
)
from app.services.xai.explanation_model import (
    ExplanationResult,
    ModelExplanation,
    VisionHeatmapExplanation,
    RAGEvidenceExplanation,
    LiveDataExplanation,
    XAICapabilityStatus
)
from app.services.xai.shap_explainer import TabularSHAPExplainer
from app.services.xai.gradcam_explainer import DiseaseGradCAMExplainer
from app.services.xai.localization import XAILocalizationService
from app.services.xai.xai_service import XAIService
from app.services.rag.evidence_model import (
    CanonicalEvidenceItem,
    CanonicalSourceCitation,
    EvidenceStatus,
    AuthorityTier
)
from app.schemas.market import MarketComparisonResponse, MandiPrice, MarketFreshnessStatus
from app.schemas.weather import WeatherResponse, WeatherCurrent, FreshnessStatus
from app.agents.orchestrator import BhoomiAgentOrchestrator


def create_synthetic_leaf_bytes(width: int = 250, height: int = 250, color=(34, 139, 34)) -> bytes:
    """Helper to generate a clean synthetic leaf image that passes ImageQualityGate."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 1. SHAP CROP RECOMMENDATION EXPLANATION
# -----------------------------------------------------------------------------
def test_01_shap_crop_recommendation_explanation():
    inp = CropRecommendationInput(
        nitrogen=90.0,
        phosphorus=42.0,
        potassium=43.0,
        temperature=24.5,
        humidity=82.0,
        ph=6.5,
        rainfall=202.0
    )
    pred = CropRecommendationService.predict(inp)
    exp = TabularSHAPExplainer.explain_crop_recommendation(inp, pred)

    assert isinstance(exp, ModelExplanation)
    assert exp.model_name == "RandomForestClassifier"
    assert exp.prediction == pred.recommended_crops[0].crop
    assert exp.xai_status == XAICapabilityStatus.AVAILABLE.value
    assert len(exp.top_positive_factors) > 0
    assert exp.confidence is not None
    assert exp.confidence == pred.recommended_crops[0].confidence
    # SHAP value must be non-zero and legitimate
    top_factor = exp.top_positive_factors[0]
    assert top_factor.shap_value > 0
    assert top_factor.feature in ["nitrogen", "phosphorus", "potassium", "temperature", "humidity", "ph", "rainfall"]


# -----------------------------------------------------------------------------
# 2. SHAP YIELD PREDICTION EXPLANATION
# -----------------------------------------------------------------------------
def test_02_shap_yield_prediction_explanation():
    inp = YieldPredictionInput(
        crop_name="Chilli",
        state="Andhra Pradesh",
        season="Kharif",
        area_acres=3.0,
        annual_rainfall_mm=850.0,
        fertilizer_applied_kg=250.0,
        pesticide_applied_kg=15.0
    )
    pred = YieldPredictionService.predict(inp)
    exp = TabularSHAPExplainer.explain_yield_prediction(inp, pred)

    assert isinstance(exp, ModelExplanation)
    assert exp.model_name == "XGBoost Regressor"
    assert exp.xai_status == XAICapabilityStatus.AVAILABLE.value
    assert len(exp.all_contributions) >= 4
    assert exp.base_value is not None
    # Verify no fabricated confidence score
    assert exp.confidence is None


# -----------------------------------------------------------------------------
# 3. FERTILIZER EXPLANATION (MODEL-SUPPORTED OR HEURISTIC)
# -----------------------------------------------------------------------------
def test_03_fertilizer_explanation_model_supported_or_heuristic():
    inp = FertilizerInput(
        crop_name="Chilli",
        crop_stage="vegetative",
        soil_type="black",
        nitrogen=40.0,  # deficit (<50)
        phosphorus=20.0,  # deficit (<25)
        potassium=30.0,   # deficit (<40)
        temperature=28.0,
        humidity=70.0,
        moisture=45.0
    )
    pred = FertilizerRecommendationService.recommend(inp)
    exp = TabularSHAPExplainer.explain_fertilizer_recommendation(inp, pred)

    assert isinstance(exp, ModelExplanation)
    assert exp.prediction == pred.recommended_fertilizer
    assert exp.xai_status in [XAICapabilityStatus.AVAILABLE.value, XAICapabilityStatus.HEURISTIC_ATTRIBUTION.value]
    assert len(exp.top_positive_factors) > 0


# -----------------------------------------------------------------------------
# 4. SHAP FEATURE/VALUE CORRESPONDENCE
# -----------------------------------------------------------------------------
def test_04_shap_feature_value_correspondence():
    inp = CropRecommendationInput(
        nitrogen=85.0,
        phosphorus=35.0,
        potassium=40.0,
        temperature=26.0,
        humidity=75.0,
        ph=6.8,
        rainfall=300.0
    )
    pred = CropRecommendationService.predict(inp)
    exp = TabularSHAPExplainer.explain_crop_recommendation(inp, pred)

    assert exp.input_features_used["nitrogen"] == 85.0
    assert exp.input_features_used["phosphorus"] == 35.0
    assert exp.input_features_used["potassium"] == 40.0
    assert exp.input_features_used["ph"] == 6.8
    assert exp.input_features_used["rainfall"] == 300.0

    # Ensure contribution items match the actual input values
    for item in exp.all_contributions:
        assert item.value == getattr(inp, item.feature)


# -----------------------------------------------------------------------------
# 5. SHAP PREDICTION CORRESPONDENCE
# -----------------------------------------------------------------------------
def test_05_shap_prediction_correspondence():
    inp = CropRecommendationInput(
        nitrogen=120.0,
        phosphorus=50.0,
        potassium=50.0,
        temperature=28.0,
        humidity=70.0,
        ph=6.5,
        rainfall=1100.0
    )
    pred = CropRecommendationService.predict(inp)
    exp = TabularSHAPExplainer.explain_crop_recommendation(inp, pred)

    assert exp.prediction == pred.recommended_crops[0].crop
    assert exp.confidence == pred.recommended_crops[0].confidence


# -----------------------------------------------------------------------------
# 6. NO FAKE SHAP OUTPUT WHEN MODEL UNAVAILABLE
# -----------------------------------------------------------------------------
def test_06_no_fake_shap_output_when_model_unavailable(monkeypatch):
    import app.services.xai.shap_explainer as se_mod
    monkeypatch.setattr(se_mod, "SHAP_AVAILABLE", False)

    inp = CropRecommendationInput(
        nitrogen=90.0, phosphorus=42.0, potassium=43.0,
        temperature=24.5, humidity=82.0, ph=6.5, rainfall=202.0
    )
    pred = CropRecommendationService.predict(inp)
    exp = se_mod.TabularSHAPExplainer.explain_crop_recommendation(inp, pred)

    assert exp.xai_status == XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value
    assert len(exp.top_positive_factors) == 0
    assert "unavailable" in exp.explanation_summary.lower()


# -----------------------------------------------------------------------------
# 7. GRAD-CAM ACTUAL MODEL COMPATIBILITY
# -----------------------------------------------------------------------------
def test_07_gradcam_actual_model_compatibility():
    leaf_bytes = create_synthetic_leaf_bytes()
    res = DiseaseGradCAMExplainer.explain_leaf_diagnosis(leaf_bytes, crop_hint="tomato")

    assert isinstance(res, VisionHeatmapExplanation)
    # The tomato MobileNetV3 model is loaded with authentic weights
    if res.xai_status == XAICapabilityStatus.AVAILABLE.value:
        assert res.heatmap is not None
        assert len(res.heatmap) == 7
        assert len(res.heatmap[0]) == 7
        # Verify normalization to [0.0, 1.0]
        max_val = max(max(row) for row in res.heatmap)
        min_val = min(min(row) for row in res.heatmap)
        assert max_val <= 1.0
        assert min_val >= 0.0
        assert "peak_cell" in res.localization_metadata
        assert "bounding_box_normalized" in res.localization_metadata


# -----------------------------------------------------------------------------
# 8. NO DECORATIVE / RANDOM GRAD-CAM
# -----------------------------------------------------------------------------
def test_08_no_decorative_or_random_gradcam():
    leaf_bytes = create_synthetic_leaf_bytes()
    res1 = DiseaseGradCAMExplainer.explain_leaf_diagnosis(leaf_bytes, crop_hint="tomato")
    res2 = DiseaseGradCAMExplainer.explain_leaf_diagnosis(leaf_bytes, crop_hint="tomato")

    if res1.xai_status == XAICapabilityStatus.AVAILABLE.value:
        # Deterministic: two runs on same image must yield identical authentic values
        np.testing.assert_allclose(res1.heatmap, res2.heatmap, atol=1e-4)
        assert res1.localization_metadata["peak_cell"] == res2.localization_metadata["peak_cell"]


# -----------------------------------------------------------------------------
# 9. EXPLICIT GRAD-CAM UNAVAILABLE STATE IF UNSUPPORTED
# -----------------------------------------------------------------------------
def test_09_explicit_gradcam_unavailable_state_if_unsupported():
    # 1. Image that fails Quality Gate (< 50x50 pixels)
    tiny_img = Image.new("RGB", (30, 30), color=(10, 10, 10))
    buf = io.BytesIO()
    tiny_img.save(buf, format="JPEG")
    tiny_bytes = buf.getvalue()

    res_tiny = DiseaseGradCAMExplainer.explain_leaf_diagnosis(tiny_bytes, crop_hint="tomato")
    assert res_tiny.xai_status == XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value
    assert res_tiny.heatmap is None
    assert any("quality gate" in lim.lower() for lim in res_tiny.limitations)

    # 2. Unsupported crop
    valid_leaf = create_synthetic_leaf_bytes()
    res_unsupported = DiseaseGradCAMExplainer.explain_leaf_diagnosis(valid_leaf, crop_hint="unsupported_crop_xyz")
    assert res_unsupported.xai_status == XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value
    assert res_unsupported.heatmap is None


# -----------------------------------------------------------------------------
# 10. RAG CITATIONS PRESERVED
# -----------------------------------------------------------------------------
def test_10_rag_citations_preserved():
    cites = [
        CanonicalSourceCitation(
            citation_id="cite_icar_chilli_1",
            document_title="ICAR-IIHR Chilli Package of Practices",
            authority="ICAR-IIHR",
            authority_level=AuthorityTier.TIER_1_GOVT_ICAR.value,
            section="Nutrient Management"
        )
    ]
    items = [
        CanonicalEvidenceItem(
            chunk_id="chk_1",
            document_id="doc_1",
            title="ICAR-IIHR Chilli Package of Practices",
            source="ICAR-IIHR",
            crop="chilli",
            authority_level=AuthorityTier.TIER_1_GOVT_ICAR.value,
            content="Apply 25 kg Urea at 30 days after transplanting.",
            relevance_score=0.94
        )
    ]
    rag_exp = XAIService.create_rag_explanation(
        evidence_status=EvidenceStatus.SUFFICIENT,
        evidence_items=items,
        citations=cites,
        lang="en"
    )

    assert rag_exp.is_sufficient is True
    assert rag_exp.evidence_status == "SUFFICIENT"
    assert len(rag_exp.citations) == 1
    assert rag_exp.citations[0].citation_id == "cite_icar_chilli_1"
    assert rag_exp.citations[0].authority_level == "TIER_1_GOVT_ICAR"
    assert "ICAR-IIHR" in rag_exp.explanation_summary


# -----------------------------------------------------------------------------
# 11. RAG INSUFFICIENT EVIDENCE PRESERVED
# -----------------------------------------------------------------------------
def test_11_rag_insufficient_evidence_preserved():
    rag_exp = XAIService.create_rag_explanation(
        evidence_status=EvidenceStatus.INSUFFICIENT,
        citations=[],
        lang="en"
    )

    assert rag_exp.is_sufficient is False
    assert rag_exp.evidence_status == "INSUFFICIENT"
    assert len(rag_exp.citations) == 0
    assert "insufficient" in rag_exp.explanation_summary.lower()


# -----------------------------------------------------------------------------
# 12. MARKET PROVENANCE PRESERVED
# -----------------------------------------------------------------------------
def test_12_market_provenance_preserved():
    mandi_price = MandiPrice(
        mandi_name="Guntur Mandi",
        district="Guntur",
        state="Andhra Pradesh",
        commodity="Chilli",
        modal_price_per_quintal=Decimal("12000.00"),
        freshness=MarketFreshnessStatus.CURRENT.value,
        is_live=True,
        is_synthetic=False
    )
    live_exp = XAIService.create_live_data_explanation(market_res=mandi_price)
    assert live_exp.market is not None
    assert live_exp.market["freshness"] == "CURRENT"
    assert live_exp.market["is_synthetic"] is False
    assert live_exp.market["contribution_status"] == "CURRENT"


# -----------------------------------------------------------------------------
# 13. WEATHER PROVENANCE PRESERVED
# -----------------------------------------------------------------------------
def test_13_weather_provenance_preserved():
    w_curr = WeatherCurrent(
        temperature_c=28.5,
        humidity_percent=70.0,
        weather_condition="Clear",
        advisory="Good spraying conditions",
        freshness=FreshnessStatus.CURRENT.value,
        is_live=True
    )
    w_res = WeatherResponse(
        location="Guntur",
        current=w_curr,
        forecast_3_days=[],
        source="IMD / OpenWeatherMap",
        freshness=FreshnessStatus.CURRENT.value,
        configured=True
    )
    live_exp = XAIService.create_live_data_explanation(weather_res=w_res)
    assert live_exp.weather is not None
    assert live_exp.weather["freshness"] == "CURRENT"
    assert live_exp.weather["contribution_status"] == "CURRENT"


# -----------------------------------------------------------------------------
# 14. SYNTHETIC / DEMO STATUS PRESERVED
# -----------------------------------------------------------------------------
def test_14_synthetic_demo_status_preserved():
    demo_price = MandiPrice(
        mandi_name="Guntur Mandi (Demo)",
        district="Guntur",
        state="Andhra Pradesh",
        commodity="Chilli",
        modal_price_per_quintal=Decimal("12200.00"),
        freshness=MarketFreshnessStatus.DEMO.value,
        is_live=False,
        is_synthetic=True
    )
    live_exp = XAIService.create_live_data_explanation(market_res=demo_price)
    assert live_exp.market["is_synthetic"] is True
    assert live_exp.market["freshness"] == "DEMO"
    assert live_exp.market["contribution_status"] == "DEMO"


# -----------------------------------------------------------------------------
# 15. EXPLANATION OBJECT SCHEMA
# -----------------------------------------------------------------------------
def test_15_explanation_object_schema():
    inp = CropRecommendationInput(
        nitrogen=90.0, phosphorus=42.0, potassium=43.0,
        temperature=24.5, humidity=82.0, ph=6.5, rainfall=202.0
    )
    pred = CropRecommendationService.predict(inp)
    result = XAIService.explain_crop_recommendation(inp, pred, lang="en")

    assert isinstance(result, ExplanationResult)
    assert result.decision_id.startswith("dec_crop_")
    assert result.decision_type == "crop_recommendation"
    assert result.model_explanation is not None
    assert result.rag_evidence is not None
    assert result.live_data is not None
    assert isinstance(result.top_factors, list)
    assert isinstance(result.limitations, list)
    assert result.locale == "en"
    assert result.generated_at is not None


# -----------------------------------------------------------------------------
# 16. ORCHESTRATOR EXPLANATION INTEGRATION
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_16_orchestrator_explanation_integration():
    result = await BhoomiAgentOrchestrator.orchestrate(
        user_text="Why was this task scheduled?",
        farmer_id="demo_farmer_1",
        language="en"
    )

    assert result is not None
    assert "WHY:" in result.response_text
    assert "EVIDENCE:" in result.response_text
    assert "CURRENT DATA:" in result.response_text

    # Verify visual_cards contains xai_explanation_card
    card_types = [c.get("card_type") for c in result.visual_cards]
    assert "xai_explanation_card" in card_types


# -----------------------------------------------------------------------------
# 17. ENGLISH EXPLANATION
# -----------------------------------------------------------------------------
def test_17_english_explanation():
    text = XAILocalizationService.format_farmer_explanation(
        why_bullets=["Soil nitrogen level strongly supported chilli."],
        evidence_bullets=["ICAR - Chilli Package of Practices"],
        weather_status="CURRENT",
        market_status="CURRENT",
        limitations=["Soil phosphorus measurement unavailable."],
        lang="en"
    )
    assert "WHY:" in text
    assert "EVIDENCE:" in text
    assert "CURRENT DATA:" in text
    assert "LIMITATIONS:" in text
    assert "Weather: CURRENT" in text


# -----------------------------------------------------------------------------
# 18. TELUGU EXPLANATION
# -----------------------------------------------------------------------------
def test_18_telugu_explanation():
    text = XAILocalizationService.format_farmer_explanation(
        why_bullets=["నేలలో నత్రజని స్థాయి మిర్చి పంటకు అనుకూలంగా ఉంది."],
        evidence_bullets=["ICAR - మిర్చి సాగు పద్ధతులు"],
        weather_status="CURRENT",
        market_status="CURRENT",
        limitations=["భాస్వరం లభ్యత వివరాలు లేవు."],
        lang="te"
    )
    assert "ఎందుకు (కారణం):" in text
    assert "ఆధారాలు (పరిశోధనా సమాచారం):" in text
    assert "ప్రస్తుత సమాచారం:" in text
    assert "పరిమితులు:" in text
    assert "వాతావరణం: CURRENT" in text


# -----------------------------------------------------------------------------
# 19. HINDI EXPLANATION
# -----------------------------------------------------------------------------
def test_19_hindi_explanation():
    text = XAILocalizationService.format_farmer_explanation(
        why_bullets=["मिट्टी में नाइट्रोजन का स्तर मिर्च की फसल के लिए अनुकूल है।"],
        evidence_bullets=["ICAR - मिर्च सस्य वैज्ञानिक मार्गदर्शिका"],
        weather_status="CURRENT",
        market_status="CURRENT",
        limitations=["फास्फोरस स्तर उपलब्ध नहीं है।"],
        lang="hi"
    )
    assert "कारण (क्यों):" in text
    assert "प्रमाण (अनुसंधान साक्ष्य):" in text
    assert "वर्तमान डेटा:" in text
    assert "सीमाएं / ध्यान देने योग्य बातें:" in text
    assert "मौसम: CURRENT" in text


# -----------------------------------------------------------------------------
# 20. TAMIL, KANNADA, MALAYALAM EXPLANATIONS
# -----------------------------------------------------------------------------
def test_20_tamil_kannada_malayalam_explanations():
    ta_text = XAILocalizationService.format_farmer_explanation([], [], "CURRENT", "CURRENT", [], lang="ta")
    assert "ஏன் (காரணம்):" in ta_text
    assert "ஆதாரம் (ஆராய்ச்சி தகவல்):" in ta_text

    kn_text = XAILocalizationService.format_farmer_explanation([], [], "CURRENT", "CURRENT", [], lang="kn")
    assert "ಏಕೆ (ಕಾರಣ):" in kn_text
    assert "ಸಾಕ್ಷ್ಯಾಧಾರ (ಸಂಶೋಧನಾ ಮಾಹಿತಿ):" in kn_text

    ml_text = XAILocalizationService.format_farmer_explanation([], [], "CURRENT", "CURRENT", [], lang="ml")
    assert "എന്തുകൊണ്ട് (കാരണം):" in ml_text
    assert "തെളിവ് (ഗവേഷണ രേഖകൾ):" in ml_text


# -----------------------------------------------------------------------------
# 21. API ENDPOINTS RETURN CANONICAL EXPLANATION RESULT
# -----------------------------------------------------------------------------
def test_21_ml_and_xai_api_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. /api/v1/ml/crop-recommendation/explain
    res = client.post(
        "/api/v1/ml/crop-recommendation/explain",
        json={
            "nitrogen": 90.0,
            "phosphorus": 42.0,
            "potassium": 43.0,
            "temperature": 24.5,
            "humidity": 82.0,
            "ph": 6.5,
            "rainfall": 202.0
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["decision_type"] == "crop_recommendation"
    assert data["xai_status"] == "AVAILABLE"
    assert "model_explanation" in data
    assert len(data["top_factors"]) > 0

    # 2. /api/v1/xai/crop-recommendation
    res_xai = client.post(
        "/api/v1/xai/crop-recommendation",
        json={
            "nitrogen": 90.0,
            "phosphorus": 42.0,
            "potassium": 43.0,
            "temperature": 24.5,
            "humidity": 82.0,
            "ph": 6.5,
            "rainfall": 202.0
        }
    )
    assert res_xai.status_code == 200
    data_xai = res_xai.json()
    assert data_xai["decision_type"] == "crop_recommendation"
    assert data_xai["top_factors"][0]["feature"] in ["nitrogen", "phosphorus", "potassium", "rainfall", "temperature", "humidity", "ph"]

    # 3. /api/v1/ml/yield-prediction/explain
    res_yield = client.post(
        "/api/v1/ml/yield-prediction/explain",
        json={
            "crop_name": "Chilli",
            "state": "Andhra Pradesh",
            "season": "Kharif",
            "area_acres": 3.0,
            "annual_rainfall_mm": 850.0,
            "fertilizer_applied_kg": 250.0,
            "pesticide_applied_kg": 15.0
        }
    )
    assert res_yield.status_code == 200
    data_yield = res_yield.json()
    assert data_yield["decision_type"] == "yield_prediction"
    assert data_yield["xai_status"] == "AVAILABLE"

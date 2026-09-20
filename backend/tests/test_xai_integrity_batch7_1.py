"""
BHOOMI V2 — MASTER STABILIZATION BATCH 7.1
REGRESSION TEST SUITE: XAI INTEGRITY, PROVENANCE, THRESHOLDS & UNIT CONSISTENCY

Tests cover:
1. Production provider failure != mock data; provider failure == UNAVAILABLE (is_synthetic=False)
2. Explicit demo mock == DEMO/SYNTHETIC (is_synthetic=True)
3. Canonical RAG threshold (0.50): boundary tests at 0.49, 0.50, 0.51
4. Yield prediction unit consistency: native t/ha, display quintals/acre, SHAP correspondence, and conversion factor 4.04686
"""

import pytest
import httpx
from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.core.config import settings
from app.schemas.weather import WeatherResponse, WeatherCurrent, FreshnessStatus
from app.schemas.market import MarketComparisonResponse, MandiPrice, MarketFreshnessStatus
from app.services.weather.weather_service import WeatherService
from app.services.market.market_service import MarketService
from app.services.weather.weather_provider import WeatherProviderFactory, MockWeatherProvider
from app.services.market.market_provider import MarketProviderFactory, MockMarketDataProvider
from app.services.xai.xai_service import XAIService
from app.services.xai.explanation_model import (
    LiveDataExplanation,
    ModelExplanation,
    XAICapabilityStatus,
    ExplanationResult
)
from app.services.xai.shap_explainer import TabularSHAPExplainer
from app.services.yield_prediction.yield_service import (
    YieldPredictionService,
    YieldPredictionInput,
    YieldPredictionOutput
)
from app.services.rag.evidence_model import (
    RAG_SUFFICIENCY_THRESHOLD,
    XAI_EVIDENCE_DISPLAY_THRESHOLD,
    EvidenceStatus,
    CanonicalEvidenceItem
)
from app.services.rag.verification_service import EvidenceSufficiencyGate


# =============================================================================
# TASK 1: PRODUCTION PROVIDER FALLBACK SEMANTICS & PROVENANCE
# =============================================================================

@pytest.mark.asyncio
async def test_production_weather_failure_yields_unavailable_not_mock():
    """
    PROVENANCE GUARANTEE:
    In production (DEMO_MODE=False), when the live weather provider fails,
    WeatherService MUST return freshness=UNAVAILABLE and current measurements null.
    It MUST NOT serve synthetic or mock telemetry.
    """
    with patch("app.core.config.settings.DEMO_MODE", False):
        with patch("app.core.config.settings.APP_ENV", "production"):
            with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectTimeout("Connection timed out to Open-Meteo")):
                res = await WeatherService.get_weather(location="Guntur", lat=16.5, lon=80.6)
                
                assert res.freshness == FreshnessStatus.UNAVAILABLE.value
                assert res.provider_status in ["UNAVAILABLE", "DEGRADED"]
                assert res.current.temperature_c is None
                assert res.forecast_3_days == []
                # Ensure no synthetic data leak
                assert res.source != "mock_weather"


def test_xai_live_weather_explanation_marks_failed_provider_as_unavailable_not_synthetic():
    """
    XAI INTEGRITY GUARANTEE:
    When live weather is UNAVAILABLE, LiveDataExplanation MUST have:
    - freshness == UNAVAILABLE
    - is_synthetic == False (NEVER True!)
    - contribution_status == UNAVAILABLE
    """
    failed_weather = WeatherResponse(
        location="Guntur, Andhra Pradesh",
        latitude=16.3,
        longitude=80.4,
        source="open_meteo",
        provider_type="open_meteo",
        provider_status="UNAVAILABLE",
        freshness=FreshnessStatus.UNAVAILABLE.value,
        forecast_3_days=[],
        current=WeatherCurrent(
            temperature_c=None,
            weather_condition="Service Unavailable",
            advisory="Weather service unavailable",
            freshness=FreshnessStatus.UNAVAILABLE.value,
            is_live=False
        )
    )

    xai_live = XAIService.create_live_data_explanation(
        weather_res=failed_weather,
        market_res=None
    )

    assert xai_live.weather["provider"] == "open_meteo"
    assert xai_live.weather["freshness"] == "UNAVAILABLE"
    assert xai_live.weather["is_synthetic"] is False  # CRITICAL: not synthetic!
    assert xai_live.weather["contribution_status"] == "UNAVAILABLE"
    assert "unavailable" in xai_live.summary.lower()


@pytest.mark.asyncio
async def test_production_market_failure_yields_unavailable_not_benchmark():
    """
    PROVENANCE GUARANTEE:
    In production (DEMO_MODE=False), when live Mandi API fails,
    MarketService MUST return freshness=UNAVAILABLE and mandi_options=[].
    It MUST NOT serve synthetic or benchmark prices as current live prices.
    """
    with patch("app.core.config.settings.DEMO_MODE", False):
        with patch("app.core.config.settings.APP_ENV", "production"):
            with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectTimeout("Mandi API connection failed")):
                res = await MarketService.get_mandi_prices("Chilli", "Andhra Pradesh")
                
                assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
                assert res.provider_status in ["UNAVAILABLE", "DEGRADED"]
                assert len(res.mandi_options) == 0
                assert res.source != "mock_market"


def test_xai_live_market_explanation_marks_failed_provider_as_unavailable_not_synthetic():
    """
    XAI INTEGRITY GUARANTEE:
    When live market is UNAVAILABLE, LiveDataExplanation MUST have:
    - freshness == UNAVAILABLE
    - is_synthetic == False (NEVER True!)
    - contribution_status == UNAVAILABLE
    """
    failed_market = MarketComparisonResponse(
        commodity="Chilli",
        state="Andhra Pradesh",
        freshness=MarketFreshnessStatus.UNAVAILABLE.value,
        provider_status="UNAVAILABLE",
        source="data_gov",
        mandi_options=[]
    )

    xai_live = XAIService.create_live_data_explanation(
        weather_res=None,
        market_res=failed_market
    )

    assert xai_live.market["provider"] == "data_gov"
    assert xai_live.market["freshness"] == "UNAVAILABLE"
    assert xai_live.market["is_synthetic"] is False  # CRITICAL: not synthetic!
    assert xai_live.market["contribution_status"] == "UNAVAILABLE"
    assert "unavailable" in xai_live.summary.lower()


def test_demo_mock_mode_is_explicitly_flagged_as_synthetic():
    """
    DEMO CONTRACT GUARANTEE:
    Demo mode or synthetic fallback MUST visibly declare is_synthetic=True
    and freshness in ['DEMO', 'SYNTHETIC'].
    """
    mock_weather = WeatherResponse(
        location="Demo Station",
        latitude=16.3,
        longitude=80.4,
        source="mock_weather",
        provider_type="mock_weather",
        provider_status="DEMO_ACTIVE",
        freshness=FreshnessStatus.DEMO.value,
        forecast_3_days=[],
        current=WeatherCurrent(
            temperature_c=28.5,
            humidity_percent=65.0,
            rainfall_mm=0.0,
            wind_speed_kmh=12.0,
            advisory="Normal conditions (Demo)",
            freshness=FreshnessStatus.DEMO.value,
            is_live=False
        )
    )

    mock_market = MarketComparisonResponse(
        commodity="Chilli",
        state="Andhra Pradesh",
        freshness=MarketFreshnessStatus.DEMO.value,
        provider_status="DEMO_ACTIVE",
        source="mock_market",
        is_synthetic=True,
        mandi_options=[
            MandiPrice(
                mandi_name="Guntur Mandi",
                district="Guntur",
                state="Andhra Pradesh",
                commodity="Chilli",
                modal_price_per_quintal=Decimal("18500"),
                min_price_per_quintal=Decimal("17000"),
                max_price_per_quintal=Decimal("19500"),
                transport_cost_per_quintal=Decimal("200"),
                selling_cost_per_quintal=Decimal("150"),
                arrival_date="2026-09-20",
                freshness=MarketFreshnessStatus.DEMO.value,
                is_synthetic=True
            )
        ]
    )

    xai_live = XAIService.create_live_data_explanation(
        weather_res=mock_weather,
        market_res=mock_market
    )

    # Both weather and market should declare is_synthetic=True
    assert xai_live.weather["is_synthetic"] is True
    assert xai_live.weather["freshness"] == "DEMO"

    assert xai_live.market["is_synthetic"] is True
    assert xai_live.market["freshness"] == "DEMO"


# =============================================================================
# TASK 2A: RAG EVIDENCE THRESHOLD CONSISTENCY
# =============================================================================

def test_canonical_rag_threshold_constants():
    """
    THRESHOLD GUARANTEE:
    Confirm RAG_SUFFICIENCY_THRESHOLD == 0.50 and XAI_EVIDENCE_DISPLAY_THRESHOLD == 0.50.
    Verify no accidental 0.70 threshold is used for retrieval sufficiency or display.
    """
    assert RAG_SUFFICIENCY_THRESHOLD == 0.50
    assert XAI_EVIDENCE_DISPLAY_THRESHOLD == 0.50
    assert RAG_SUFFICIENCY_THRESHOLD == XAI_EVIDENCE_DISPLAY_THRESHOLD


def test_evidence_sufficiency_gate_boundary_conditions():
    """
    DETERMINISTIC SAFETY GUARANTEE:
    Test boundary scores at 0.49, 0.50, and 0.51 against EvidenceSufficiencyGate.
    - 0.49 MUST fail sufficiency (INSUFFICIENT)
    - 0.50 MUST pass sufficiency (SUFFICIENT)
    - 0.51 MUST pass sufficiency (SUFFICIENT)
    """
    # 1. Score 0.49 (< 0.50)
    item_below = CanonicalEvidenceItem(
        chunk_id="chk_1",
        document_id="doc_1",
        title="Chilli Cultivation Guide",
        source="icar_guide",
        crop="Chilli",
        content="Apply urea in split doses.",
        relevance_score=0.49
    )
    gate_eval_below = EvidenceSufficiencyGate.evaluate([item_below], target_crop="Chilli")
    assert gate_eval_below.is_sufficient is False
    assert gate_eval_below.status == EvidenceStatus.INSUFFICIENT
    assert gate_eval_below.confidence == 0.49

    # 2. Score 0.50 (== 0.50)
    item_exact = CanonicalEvidenceItem(
        chunk_id="chk_1",
        document_id="doc_1",
        title="Chilli Cultivation Guide",
        source="icar_guide",
        crop="Chilli",
        content="Apply urea in split doses.",
        relevance_score=0.50
    )
    gate_eval_exact = EvidenceSufficiencyGate.evaluate([item_exact], target_crop="Chilli")
    assert gate_eval_exact.is_sufficient is True
    assert gate_eval_exact.status == EvidenceStatus.SUFFICIENT
    assert gate_eval_exact.confidence == 0.50

    # 3. Score 0.51 (> 0.50)
    item_above = CanonicalEvidenceItem(
        chunk_id="chk_1",
        document_id="doc_1",
        title="Chilli Cultivation Guide",
        source="icar_guide",
        crop="Chilli",
        content="Apply urea in split doses.",
        relevance_score=0.51
    )
    gate_eval_above = EvidenceSufficiencyGate.evaluate([item_above], target_crop="Chilli")
    assert gate_eval_above.is_sufficient is True
    assert gate_eval_above.status == EvidenceStatus.SUFFICIENT
    assert gate_eval_above.confidence == 0.51


# =============================================================================
# TASK 2B: YIELD PREDICTION UNIT CONSISTENCY
# =============================================================================

def test_yield_prediction_unit_consistency_and_shap_alignment():
    """
    MATHEMATICAL UNIT CONSISTENCY GUARANTEE:
    - Input: area in acres, fertilizer in kg, pesticide in kg
    - XGBoost model native output space: tonnes/hectare (t/ha)
    - Converted farmer display space: quintals/acre
    - Conversion factor: 1 t/ha = 4.04686 quintals/acre
    - SHAP contribution values must be computed in native model space (t/ha)
    - Display text must show both units side-by-side with exact conversion factor
    - ModelExplanation metadata must declare native_unit, display_unit, conversion_factor
    """
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

    # 1. Verify YieldPredictionOutput mathematical consistency
    expected_display_quintals = round(pred.predicted_yield_tons_per_hectare * 4.04686, 2)
    assert abs(pred.predicted_yield_quintals_per_acre - expected_display_quintals) <= 0.05
    assert pred.unit in ["Quintals", "quintals/acre"]

    # 2. Explain prediction using TabularSHAPExplainer
    exp = TabularSHAPExplainer.explain_yield_prediction(inp, pred)

    assert exp.xai_status == XAICapabilityStatus.AVAILABLE.value
    assert exp.native_unit == "tonnes/hectare"
    assert exp.display_unit == "quintals/acre"
    assert exp.conversion_factor == 4.04686

    # 3. Verify every contribution has consistent units in display_text
    for c in exp.all_contributions:
        assert "t/ha" in c.display_text
        assert "quintals/acre" in c.display_text
        # Verify SHAP value is in reasonable t/ha scale (not inflated quintals)
        assert abs(c.shap_value) < 50.0  # t/ha delta per feature is typically < 10

    # 4. Verify summary text explicitly includes conversion notice
    assert "tonnes/hectare" in exp.explanation_summary
    assert "4.04686" in exp.explanation_summary
    assert "quintals/acre" in exp.explanation_summary


def test_yield_explanation_result_summary_consistency():
    """
    FARMER-FACING SUMMARY CONSISTENCY:
    Verify XAIService.explain_yield_prediction produces farmer-facing
    bullet points that display both units consistently without mixing.
    """
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
    result = XAIService.explain_yield_prediction(inp, pred)

    assert isinstance(result, ExplanationResult)
    assert result.decision_type == "yield_prediction"
    assert result.xai_status == XAICapabilityStatus.AVAILABLE.value
    assert result.model_explanation is not None

    # Check why_summary
    assert "t/ha" in result.why_summary
    assert "quintals/acre" in result.why_summary

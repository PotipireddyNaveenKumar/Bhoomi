"""
BHOOMI V2 — MASTER STABILIZATION BATCH 4
PROVIDER & DATA SAFETY HARDENING TEST SUITE

Verifies that:
MARKET:
1. live provider success -> returns valid MandiPrice with is_live=True
2. live provider timeout -> returns explicit UNAVAILABLE state (best_net_realization=None)
3. live provider unavailable -> returns explicit UNAVAILABLE state
4. live provider returns empty data -> returns explicit UNAVAILABLE state
5. malformed provider response -> returns explicit UNAVAILABLE state without crashing
6. production never falls back to mock (DEMO_MODE=False, APP_ENV=production)
7. demo may use mock (DEMO_MODE=True)
8. synthetic data is explicitly marked (is_synthetic=True, freshness="DEMO")

WEATHER:
9. public provider status is truthful (Open-Meteo: configured=True, requires_api_key=False)
10. missing weather fields remain null/unavailable (temperature_c=None, not 0.0)
11. stale weather is distinguishable from current weather (freshness="STALE")
12. provider failure does not become fake zero values in irrigation or spray evaluation

ORCHESTRATOR:
13. unavailable market data reaches the orchestrator as unavailable (provider_mode="UNAVAILABLE")
14. unavailable weather data reaches the orchestrator as unavailable (provider_mode="UNAVAILABLE")
15. farmer response does not invent current values when provider data is unavailable
"""

import pytest
import httpx
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from datetime import datetime, timezone, timedelta, date

from app.schemas.market import MarketComparisonResponse, MandiPrice, MarketFreshnessStatus
from app.schemas.weather import WeatherResponse, WeatherCurrent, WeatherForecastDay, FreshnessStatus
from app.services.market.market_provider import MarketProviderFactory, MockMarketDataProvider
from app.services.market.real_provider import RealMarketDataProvider
from app.services.market.market_service import MarketService
from app.services.market.cache import market_cache
from app.services.weather.weather_service import WeatherService
from app.services.weather.weather_provider import WeatherProviderFactory, MockWeatherProvider
from app.services.weather.real_provider import RealWeatherProvider
from app.services.weather.cache import weather_cache
from app.agents.orchestrator import BhoomiAgentOrchestrator, OrchestrationResult
from app.services.memory.digital_twin import DigitalTwinContext
from app.core.config import settings


@pytest.fixture(autouse=True)
def clean_caches():
    market_cache.clear()
    weather_cache.clear()
    yield
    market_cache.clear()
    weather_cache.clear()


# =============================================================================
# 1. MARKET DATA SAFETY TESTS (1 - 8)
# =============================================================================

@pytest.mark.asyncio
async def test_01_market_live_provider_success():
    """1. Live provider success returns parsed prices with is_live=True and active status."""
    mock_data = {
        "records": [
            {
                "state": "Andhra Pradesh",
                "district": "Guntur",
                "market": "Guntur APMC",
                "commodity": "Chilli",
                "modal_price": "12500",
                "min_price": "11000",
                "max_price": "13000",
                "arrival_date": date.today().strftime("%d/%m/%Y")
            }
        ]
    }
    provider = RealMarketDataProvider(api_key="valid_test_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Chilli", state="Andhra Pradesh", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.CURRENT.value
        assert res.is_live is True
        assert res.is_synthetic is False
        assert res.best_net_realization is not None
        assert res.best_net_realization > Decimal("0.00")
        assert res.provider_status == "ACTIVE"


@pytest.mark.asyncio
async def test_02_market_live_provider_timeout():
    """2. Live provider timeout returns explicit UNAVAILABLE without fabricating prices."""
    provider = RealMarketDataProvider(api_key="valid_test_key", timeout_seconds=1.0)
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Read timeout")):
        res = await provider.fetch_prices(commodity="Chilli", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
        assert res.best_net_realization is None
        assert res.mandi_options == []
        assert res.is_live is False
        assert res.provider_status == "UNAVAILABLE"
        assert "unavailable" in res.recommendation_reason.lower()


@pytest.mark.asyncio
async def test_03_market_live_provider_unavailable():
    """3. Missing or placeholder credentials returns explicit UNAVAILABLE state."""
    provider = RealMarketDataProvider(api_key=None)
    res = await provider.fetch_prices(commodity="Chilli", district="Guntur")
    assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
    assert res.best_net_realization is None
    assert res.recommended_mandi is None
    assert res.mandi_options == []
    assert res.provider_status == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_04_market_live_provider_returns_empty_data():
    """4. When provider returns zero records, returns explicit UNAVAILABLE."""
    provider = RealMarketDataProvider(api_key="valid_test_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"records": []}
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Chilli", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
        assert res.best_net_realization is None
        assert res.mandi_options == []


@pytest.mark.asyncio
async def test_05_market_malformed_provider_response():
    """5. Malformed/non-JSON or upstream 502 returns explicit UNAVAILABLE safely."""
    provider = RealMarketDataProvider(api_key="valid_test_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_resp.text = "Bad Gateway upstream error"
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Chilli", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
        assert res.best_net_realization is None


def test_06_production_never_falls_back_to_mock():
    """6. In production (APP_ENV=production), MarketProviderFactory NEVER returns mock."""
    with patch.object(settings, "APP_ENV", "production"):
        with patch.object(settings, "DEMO_MODE", False):
            # Even if 'mock' is explicitly requested, production overrides to RealMarketDataProvider
            provider = MarketProviderFactory.get_provider("mock")
            assert isinstance(provider, RealMarketDataProvider)
            assert not isinstance(provider, MockMarketDataProvider)


def test_07_demo_may_use_mock():
    """7. In explicit demo mode (non-prod, DEMO_MODE=True), mock provider is accessible."""
    with patch.object(settings, "APP_ENV", "development"):
        with patch.object(settings, "DEMO_MODE", True):
            provider = MarketProviderFactory.get_provider("mock")
            assert isinstance(provider, MockMarketDataProvider)


@pytest.mark.asyncio
async def test_08_synthetic_data_is_explicitly_marked():
    """8. Any mock/synthetic market response is strictly labeled with DEMO/SYNTHETIC."""
    provider = MockMarketDataProvider()
    res = await provider.fetch_prices(commodity="Chilli", district="Guntur")
    assert res.freshness == MarketFreshnessStatus.DEMO.value
    assert res.is_synthetic is True
    assert res.is_live is False
    assert res.provider_status == "DEMO"
    assert "DEMO" in res.recommendation_reason
    assert "Demo / Synthetic" in res.source
    for opt in res.mandi_options:
        assert opt.is_synthetic is True
        assert opt.freshness == MarketFreshnessStatus.DEMO.value


# =============================================================================
# 2. WEATHER PROVIDER SEMANTICS TESTS (9 - 12)
# =============================================================================

def test_09_public_weather_provider_status_is_truthful():
    """9. Public provider Open-Meteo reports configured=True without requiring an API key."""
    with patch.object(settings, "WEATHER_PROVIDER", "openmeteo"):
        with patch.object(settings, "WEATHER_API_KEY", None):
            status = WeatherService.get_provider_status()
            assert status["primary_weather_provider"] == "openmeteo"
            assert status["weather_configured"] is True
            assert status["weather_requires_api_key"] is False
            assert status["weather_provider_type"] == "public"
            assert status["weather_live_status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_10_missing_weather_fields_remain_null():
    """10. When weather data is unavailable, fields remain strictly None, never fake 0.0."""
    provider = RealWeatherProvider(api_key=None, provider_type="openmeteo")
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network unreachable")):
        res = await provider.get_current_and_forecast("Guntur")
        assert res.freshness == FreshnessStatus.UNAVAILABLE.value
        assert res.current.temperature_c is None
        assert res.current.rainfall_mm is None
        assert res.current.humidity_percent is None
        assert res.current.wind_speed_kmh is None
        assert res.current.rain_probability_percent is None
        assert res.forecast_3_days == []


def test_11_stale_weather_distinguishable_from_current():
    """11. Cache correctly differentiates CURRENT, CACHED, and STALE weather."""
    sample = WeatherResponse(
        location="Guntur",
        current=WeatherCurrent(temperature_c=32.0, advisory="Clear sky", freshness=FreshnessStatus.CURRENT.value),
        forecast_3_days=[],
        source="Test Weather"
    )
    key = weather_cache.make_key("Guntur", 16.3, 80.4)
    # Cached 10 mins ago -> CURRENT (< 30 min)
    weather_cache.set(key, sample, cached_at=datetime.now(timezone.utc) - timedelta(minutes=10))
    resp, freshness = weather_cache.get(key)
    assert freshness == FreshnessStatus.CURRENT.value

    # Cached 1 hour ago -> CACHED (30 min - 3 hr)
    weather_cache.set(key, sample, cached_at=datetime.now(timezone.utc) - timedelta(hours=1))
    resp, freshness = weather_cache.get(key)
    assert freshness == FreshnessStatus.CACHED.value

    # Cached 5 hours ago -> STALE (> 3 hr)
    weather_cache.set(key, sample, cached_at=datetime.now(timezone.utc) - timedelta(hours=5))
    resp, freshness = weather_cache.get(key)
    assert freshness == FreshnessStatus.STALE.value



def test_12_weather_failure_does_not_become_fake_zero_in_irrigation():
    """12. evaluate_irrigation does NOT fabricate fake 0% rain when rain telemetry is null."""
    eval_result = RealWeatherProvider.evaluate_irrigation(
        today_rain_prob=None,
        today_rainfall_mm=None,
        tomorrow_rain_prob=None,
        tomorrow_rainfall_mm=None
    )
    assert eval_result["decision"] == "INSUFFICIENT_DATA"
    assert eval_result["should_irrigate"] is None
    assert eval_result["today_rain_probability"] is None
    assert "unavailable" in eval_result["explanation"].lower()


# =============================================================================
# 3. ORCHESTRATOR & LLM SAFETY BOUNDARY TESTS (13 - 15)
# =============================================================================

@pytest.mark.asyncio
async def test_13_unavailable_market_data_reaches_orchestrator_as_unavailable():
    """13. When MarketService returns UNAVAILABLE, orchestrator sets provider_mode='UNAVAILABLE'."""
    twin = DigitalTwinContext(
        farmer_id="farmer_test_13",
        farmer_name="Suresh",
        state="Andhra Pradesh",
        district="Guntur",
        location="Guntur, Andhra Pradesh",
        total_land_acres=3.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0, "stage": "flowering"}]
    )

    unavailable_market = MarketComparisonResponse(
        commodity="Chilli",
        district="Guntur",
        state="Andhra Pradesh",
        best_net_realization=None,
        recommended_mandi=None,
        mandi_options=[],
        recommendation_reason="Service temporarily unavailable.",
        source="Unavailable",
        freshness=MarketFreshnessStatus.UNAVAILABLE.value,
        is_live=False,
        provider_status="UNAVAILABLE"
    )

    with patch("app.services.market.market_service.MarketService.get_mandi_prices", new_callable=AsyncMock) as mock_mkt:
        mock_mkt.return_value = unavailable_market
        res = await BhoomiAgentOrchestrator.orchestrate(
            user_text="What is today's chilli market price in Guntur mandi?",
            session_id="sess_mkt_safe",
            farmer_id="farmer_test_13",
            farm_id="farm_test_13",
            context=twin,
            language="en"
        )
        assert res.provider_mode == "UNAVAILABLE"
        assert "unavailable" in res.response_text.lower()
        # Verify no fake price was invented
        assert "12,000" not in res.response_text
        assert "12,200" not in res.response_text


@pytest.mark.asyncio
async def test_14_unavailable_weather_data_reaches_orchestrator_as_unavailable():
    """14. When WeatherService returns UNAVAILABLE, orchestrator sets provider_mode='UNAVAILABLE'."""
    twin = DigitalTwinContext(
        farmer_id="farmer_test_14",
        farmer_name="Suresh",
        state="Andhra Pradesh",
        district="Guntur",
        location="Guntur, Andhra Pradesh",
        total_land_acres=3.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0, "stage": "flowering"}]
    )

    unavailable_weather = WeatherResponse(
        location="Guntur",
        current=WeatherCurrent(
            temperature_c=None,
            weather_condition="Service Unavailable",
            rain_probability_percent=None,
            advisory="Weather data unavailable.",
            freshness=FreshnessStatus.UNAVAILABLE.value
        ),
        forecast_3_days=[],
        source="Unavailable",
        freshness=FreshnessStatus.UNAVAILABLE.value,
        provider_type="UNAVAILABLE"
    )

    with patch("app.services.weather.weather_service.WeatherService.get_weather", new_callable=AsyncMock) as mock_wtr:
        mock_wtr.return_value = unavailable_weather
        res = await BhoomiAgentOrchestrator.orchestrate(
            user_text="What is today's weather forecast in Guntur?",
            session_id="sess_wtr_safe",
            farmer_id="farmer_test_14",
            farm_id="farm_test_14",
            context=twin,
            language="en"
        )
        assert res.provider_mode == "UNAVAILABLE"
        assert "unavailable" in res.response_text.lower()
        # Verify no fake temperature was invented
        assert "31.5" not in res.response_text


@pytest.mark.asyncio
async def test_15_spray_safety_does_not_approve_when_weather_unavailable():
    """15. Spray safety does NOT give favorable spray approval when weather is unavailable."""
    twin = DigitalTwinContext(
        farmer_id="farmer_test_15",
        farmer_name="Suresh",
        state="Andhra Pradesh",
        district="Guntur",
        location="Guntur, Andhra Pradesh",
        total_land_acres=3.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0, "stage": "flowering"}]
    )

    unavailable_weather = WeatherResponse(
        location="Guntur",
        current=WeatherCurrent(
            temperature_c=None,
            weather_condition="Service Unavailable",
            rain_probability_percent=None,
            advisory="Weather data unavailable.",
            freshness=FreshnessStatus.UNAVAILABLE.value
        ),
        forecast_3_days=[],
        source="Unavailable",
        freshness=FreshnessStatus.UNAVAILABLE.value,
        provider_type="UNAVAILABLE"
    )

    with patch("app.services.weather.weather_service.WeatherService.get_weather", new_callable=AsyncMock) as mock_wtr:
        mock_wtr.return_value = unavailable_weather
        res = await BhoomiAgentOrchestrator.orchestrate(
            user_text="Can I spray pesticide tomorrow?",
            session_id="sess_spray_safe",
            farmer_id="farmer_test_15",
            farm_id="farm_test_15",
            context=twin,
            language="en"
        )
        assert res.provider_mode == "UNAVAILABLE"
        assert "favorable for spraying" not in res.response_text.lower()
        assert "unavailable" in res.response_text.lower()

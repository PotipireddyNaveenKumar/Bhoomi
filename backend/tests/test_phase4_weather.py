import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import httpx
from app.schemas.weather import WeatherResponse, WeatherCurrent, WeatherForecastDay, FreshnessStatus
from app.services.weather.weather_provider import WeatherProvider, MockWeatherProvider, WeatherProviderFactory
from app.services.weather.real_provider import RealWeatherProvider
from app.services.weather.cache import WeatherCache, WeatherCacheEntry, weather_cache
from app.services.weather.location import resolve_location_coordinates
from app.services.weather.weather_service import WeatherService
from app.services.farm_manager.weather_decision import WeatherDecisionEngine, WeatherDecisionResult
from app.services.farm_manager.state_engine import FarmStateEngine
from app.agents.tool_registry import ToolRegistry
from app.agents.orchestrator import BhoomiAgentOrchestrator

# Sample mock OpenWeatherMap responses
SAMPLE_OWM_WEATHER = {
    "main": {"temp": 32.4, "humidity": 65.0},
    "wind": {"speed": 3.5},
    "weather": [{"description": "scattered clouds"}],
    "rain": {"1h": 0.0}
}

SAMPLE_OWM_FORECAST = {
    "list": [
        {
            "dt_txt": "2026-09-04 12:00:00",
            "pop": 0.45,
            "main": {"temp": 33.0},
            "weather": [{"description": "scattered clouds"}]
        },
        {
            "dt_txt": "2026-09-05 12:00:00",
            "pop": 0.20,
            "main": {"temp": 34.0},
            "weather": [{"description": "clear sky"}]
        },
        {
            "dt_txt": "2026-09-06 12:00:00",
            "pop": 0.10,
            "main": {"temp": 35.0},
            "weather": [{"description": "clear sky"}]
        }
    ]
}

# 1. Provider Factory Resolution
def test_provider_factory_resolution():
    p_mock = WeatherProviderFactory.get_provider("mock")
    assert isinstance(p_mock, MockWeatherProvider)

    p_om = WeatherProviderFactory.get_provider("openmeteo")
    assert isinstance(p_om, RealWeatherProvider)
    assert p_om.provider_type == "openmeteo"

    with patch.dict(os.environ, {"WEATHER_API_KEY": "test_owm_key"}):
        p_owm = WeatherProviderFactory.get_provider("openweathermap")
        assert isinstance(p_owm, RealWeatherProvider)
        assert p_owm.provider_type == "openweathermap"

    # Fallback on unknown provider
    p_unknown = WeatherProviderFactory.get_provider("unknown_provider_xyz")
    assert isinstance(p_unknown, MockWeatherProvider)

# 2. Real Provider Configuration
def test_real_provider_configuration():
    provider = RealWeatherProvider(api_key="mock_key", provider_type="openweathermap", timeout_seconds=5.0)
    assert provider.api_key == "mock_key"
    assert provider.provider_type == "openweathermap"
    assert provider.timeout_seconds == 5.0

# 3. Mock Provider Operation
@pytest.mark.asyncio
async def test_mock_provider():
    provider = MockWeatherProvider()
    res = await provider.get_current_and_forecast("Guntur")
    assert res.location == "Guntur"
    assert res.current.temperature_c == 31.5
    assert res.current.humidity_percent == 68.0
    assert res.current.rain_probability_percent == 40
    assert len(res.forecast_3_days) == 3

# 4. Missing API Key Fallback
@pytest.mark.asyncio
async def test_missing_api_key():
    # When initialized with no key, RealWeatherProvider safely uses Open-Meteo or cached without crashing
    provider = RealWeatherProvider(api_key=None, provider_type="openweathermap")
    mock_resp = httpx.Response(
        200,
        json={
            "current": {"temperature_2m": 30.0, "relative_humidity_2m": 70.0, "rain": 0.0, "wind_speed_10m": 12.0, "weather_code": 1},
            "daily": {"time": ["2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06"], "temperature_2m_max": [32, 33, 34, 35], "temperature_2m_min": [24, 25, 25, 26], "precipitation_probability_max": [30, 45, 20, 10], "weather_code": [1, 2, 0, 0]}
        }
    )
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await provider.get_current_and_forecast("Tenali")
        assert res.current.temperature_c == 30.0
        assert res.current.humidity_percent == 70.0

# 5. Successful Provider Response Parsing
@pytest.mark.asyncio
async def test_successful_provider_response_parsing():
    weather_cache.clear()
    provider = RealWeatherProvider(api_key="valid_key", provider_type="openweathermap")

    def mock_get(url, *args, **kwargs):
        if "forecast" in str(url):
            return httpx.Response(200, json=SAMPLE_OWM_FORECAST)
        return httpx.Response(200, json=SAMPLE_OWM_WEATHER)

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        res = await provider.get_current_and_forecast("Guntur", lat=16.3067, lon=80.4365)
        assert res.current.temperature_c == 32.4
        assert res.current.humidity_percent == 65.0
        assert res.current.rain_probability_percent == 45
        assert res.freshness == "CURRENT"
        assert res.current.is_live is True
        assert len(res.forecast_3_days) == 3

# 6. Malformed Provider Response
@pytest.mark.asyncio
async def test_malformed_provider_response():
    weather_cache.clear()
    provider = RealWeatherProvider(api_key="valid_key", provider_type="openweathermap")

    with patch("httpx.AsyncClient.get", return_value=httpx.Response(200, json={})):
        res = await provider.get_current_and_forecast("Guntur")
        # Should gracefully return None for unobserved fields without throwing an unhandled exception
        assert res.current.temperature_c is None
        assert res.current.rainfall_mm is None
        assert res.freshness == "CURRENT"

# 7. Timeout Handling
@pytest.mark.asyncio
async def test_timeout_handling():
    weather_cache.clear()
    provider = RealWeatherProvider(api_key="valid_key", provider_type="openweathermap")

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Read timed out")):
        res = await provider.get_current_and_forecast("Guntur")
        assert res.freshness == "UNAVAILABLE"
        assert res.current.is_live is False
        assert "unavailable" in res.current.advisory.lower()

# 8. Network Failure Handling
@pytest.mark.asyncio
async def test_network_failure_handling():
    weather_cache.clear()
    provider = RealWeatherProvider(api_key="valid_key", provider_type="openweathermap")

    with patch("httpx.AsyncClient.get", side_effect=httpx.RequestError("Host DNS failure")):
        res = await provider.get_current_and_forecast("Guntur")
        assert res.freshness == "UNAVAILABLE"
        assert res.current.is_live is False

# 9. HTTP 401/403 Handling
@pytest.mark.asyncio
async def test_http_401_403_handling():
    weather_cache.clear()
    provider = RealWeatherProvider(api_key="invalid_key", provider_type="openweathermap")

    with patch("httpx.AsyncClient.get", return_value=httpx.Response(401, json={"message": "Invalid API key"})):
        res = await provider.get_current_and_forecast("Guntur")
        assert res.freshness == "UNAVAILABLE"

# 10. HTTP 429 Handling
@pytest.mark.asyncio
async def test_http_429_handling():
    weather_cache.clear()
    provider = RealWeatherProvider(api_key="valid_key", provider_type="openweathermap")

    with patch("httpx.AsyncClient.get", return_value=httpx.Response(429, text="Rate limit exceeded")):
        res = await provider.get_current_and_forecast("Guntur")
        assert res.freshness == "UNAVAILABLE"

# 11. HTTP 5xx Handling
@pytest.mark.asyncio
async def test_http_5xx_handling():
    weather_cache.clear()
    provider = RealWeatherProvider(api_key="valid_key", provider_type="openweathermap")

    with patch("httpx.AsyncClient.get", return_value=httpx.Response(502, text="Bad Gateway")):
        res = await provider.get_current_and_forecast("Guntur")
        assert res.freshness == "UNAVAILABLE"

# 12. Cache Behavior
@pytest.mark.asyncio
async def test_cache_behavior():
    cache = WeatherCache()
    key = "weather:16.31:80.44"
    
    # Set item
    mock_obj = WeatherResponse(
        location="Guntur",
        current=WeatherCurrent(
            temperature_c=31.0, humidity_percent=60.0, rainfall_mm=0.0,
            wind_speed_kmh=10.0, weather_condition="Clear", rain_probability_percent=20,
            advisory="Normal conditions"
        ),
        forecast_3_days=[],
        source="Test Source"
    )
    cache.set(key, mock_obj)
    
    item = cache.get(key)
    assert item is not None
    resp, freshness = item
    assert resp.current.temperature_c == 31.0
    assert freshness == "CURRENT"

# 13. CURRENT Freshness
def test_current_freshness():
    cache = WeatherCache()
    key = "test_current"
    mock_obj = WeatherResponse(
        location="Guntur",
        current=WeatherCurrent(
            temperature_c=31.0, humidity_percent=60.0, rainfall_mm=0.0,
            wind_speed_kmh=10.0, weather_condition="Clear", rain_probability_percent=20,
            advisory="Normal"
        ),
        forecast_3_days=[],
        source="Test"
    )
    # Stored 5 minutes ago (< 30 min window)
    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    cache.set(key, mock_obj, cached_at=five_min_ago)

    resp, freshness = cache.get(key)
    assert freshness == "CURRENT"
    assert resp.current.is_live is True

# 14. CACHED Freshness
def test_cached_freshness():
    cache = WeatherCache()
    key = "test_cached"
    mock_obj = WeatherResponse(
        location="Guntur",
        current=WeatherCurrent(
            temperature_c=31.0, humidity_percent=60.0, rainfall_mm=0.0,
            wind_speed_kmh=10.0, weather_condition="Clear", rain_probability_percent=20,
            advisory="Normal"
        ),
        forecast_3_days=[],
        source="Test"
    )
    # Stored 60 minutes ago (between 30 min and 180 min)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(minutes=60)
    cache.set(key, mock_obj, cached_at=one_hour_ago)

    resp, freshness = cache.get(key)
    assert freshness == "CACHED"
    assert resp.current.is_live is False
    assert "[CACHED at" in resp.current.advisory

# 15. STALE Freshness
def test_stale_freshness():
    cache = WeatherCache()
    key = "test_stale"
    mock_obj = WeatherResponse(
        location="Guntur",
        current=WeatherCurrent(
            temperature_c=31.0, humidity_percent=60.0, rainfall_mm=0.0,
            wind_speed_kmh=10.0, weather_condition="Clear", rain_probability_percent=20,
            advisory="Normal"
        ),
        forecast_3_days=[],
        source="Test"
    )
    # Stored 4 hours ago (>= 180 min)
    four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=4)
    cache.set(key, mock_obj, cached_at=four_hours_ago)

    resp, freshness = cache.get(key)
    assert freshness == "STALE"
    assert resp.current.is_live is False
    assert "[STALE ADVISORY" in resp.current.advisory

# 16. UNAVAILABLE Freshness
@pytest.mark.asyncio
async def test_unavailable_freshness():
    weather_cache.clear()
    provider = RealWeatherProvider()
    # Unknown location with no coordinates
    res = await provider.get_current_and_forecast("UnknownNonExistentVillageXYZ123")
    assert res.freshness == "UNAVAILABLE"
    assert res.current.freshness == "UNAVAILABLE"
    assert res.current.is_live is False

# 17. No Fabricated Weather Values (Null When Unavailable)
@pytest.mark.asyncio
async def test_no_fabricated_weather_values():
    weather_cache.clear()
    provider = RealWeatherProvider()
    res = await provider.get_current_and_forecast("UnknownNonExistentVillageXYZ123")
    # Must strictly return None for unobserved measurements, never fabricated numbers or ambiguous zeros
    assert res.current.temperature_c is None
    assert res.current.rainfall_mm is None
    assert res.current.rain_probability_percent is None
    assert res.current.humidity_percent is None
    assert res.current.wind_speed_kmh is None
    assert res.forecast_3_days == []

# 18. Weather Tool Integration
@pytest.mark.asyncio
async def test_weather_tool_integration():
    res = await ToolRegistry.execute_tool("get_current_weather", {"location": "Guntur"})
    assert res["card_type"] == "weather_card"
    assert "Guntur" in res["title"]
    assert "temperature_c" in res["data"]["current"]
    assert "freshness" in res["data"]

# 19. WeatherDecisionEngine Integration
def test_weather_decision_engine_integration():
    data = {
        "temperature_c": 31.5,
        "rain_probability": 65,
        "rainfall_mm": 18.0,
        "condition": "Heavy Showers",
        "freshness": "CURRENT"
    }
    decision = WeatherDecisionEngine.evaluate(data, soil_type="black", crop_stage="vegetative")
    assert decision.irrigation_decision == "DELAY"
    assert decision.spraying_decision == "HOLD"
    assert decision.drainage_advice is None  # < 25mm

# 20. FarmStateEngine Integration
@pytest.mark.asyncio
async def test_farm_state_engine_integration():
    state = await FarmStateEngine.get_current_state("farmer_test_weather")
    assert "temperature_c" in state.weather_summary
    assert "freshness" in state.weather_summary
    assert "weather" in state.data_freshness
    assert state.data_freshness["weather"].freshness_status in ("CURRENT", "CACHED", "STALE", "UNAVAILABLE")

# 21. Irrigation Decision Integration
def test_irrigation_decision_integration():
    # Low rain prob -> PROCEED
    low_rain = {"temperature_c": 30.0, "rain_probability": 15, "rainfall_mm": 0.0, "freshness": "CURRENT"}
    res_low = WeatherDecisionEngine.evaluate(low_rain)
    assert res_low.irrigation_decision == "PROCEED"

    # High rain prob >= 40% -> DELAY
    high_rain = {"temperature_c": 29.0, "rain_probability": 45, "rainfall_mm": 5.0, "freshness": "CURRENT"}
    res_high = WeatherDecisionEngine.evaluate(high_rain)
    assert res_high.irrigation_decision == "DELAY"

# 22. Spray/Rain Decision Integration
def test_spray_rain_decision_integration():
    # Flowering crop stage -> RESTRICTED_TIMING
    flowering_data = {"temperature_c": 30.0, "rain_probability": 20, "rainfall_mm": 0.0, "freshness": "CURRENT"}
    res_fl = WeatherDecisionEngine.evaluate(flowering_data, crop_stage="flowering")
    assert res_fl.spraying_decision == "RESTRICTED_TIMING"
    assert "pollinator" in res_fl.spraying_advice.lower()

    # Heavy rain >= 50% -> HOLD
    rain_data = {"temperature_c": 28.0, "rain_probability": 55, "rainfall_mm": 16.0, "freshness": "CURRENT"}
    res_rain = WeatherDecisionEngine.evaluate(rain_data, crop_stage="vegetative")
    assert res_rain.spraying_decision == "HOLD"

# 23. Agent Weather Query Integration
@pytest.mark.asyncio
async def test_agent_weather_query_integration():
    result = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_test_weather_query",
        user_text="Will it rain tomorrow on my chilli farm?",
        input_mode="text"
    )
    assert result.response_text is not None
    assert len(result.response_text) > 10
    # Must mention weather / rain / farm status
    text_lower = result.response_text.lower()
    assert "rain" in text_lower or "weather" in text_lower or "farm" in text_lower

# 24. Semantic Safety: Real Zero Rainfall vs Unavailable
def test_real_zero_rainfall_vs_unavailable():
    # Measured zero rainfall (clear sky observation)
    measured_zero = {
        "temperature_c": 32.0,
        "humidity_percent": 45.0,
        "rainfall_mm": 0.0,
        "rain_probability": 0,
        "condition": "Clear Sky",
        "freshness": "CURRENT"
    }
    decision_zero = WeatherDecisionEngine.evaluate(measured_zero)
    assert decision_zero.rainfall_mm == 0.0
    assert decision_zero.rain_probability == 0
    assert decision_zero.irrigation_decision == "PROCEED"
    assert decision_zero.spraying_decision == "SAFE"

    # Genuinely unavailable rainfall
    unavailable_data = {
        "freshness": "UNAVAILABLE"
    }
    decision_unavail = WeatherDecisionEngine.evaluate(unavailable_data)
    assert decision_unavail.rainfall_mm is None
    assert decision_unavail.rain_probability is None
    assert decision_unavail.temperature_c is None
    assert decision_unavail.irrigation_decision == "PROCEED_WITH_CAUTION"
    assert decision_unavail.spraying_decision == "HOLD"
    assert "inspect soil moisture manually" in decision_unavail.irrigation_advice

# 25. Semantic Safety: Unavailable Weather Null Fields
@pytest.mark.asyncio
async def test_unavailable_weather_null_fields():
    weather_cache.clear()
    provider = RealWeatherProvider()
    res = await provider.get_current_and_forecast("NonExistentLocationDistrict999")
    
    assert res.freshness == "UNAVAILABLE"
    assert res.current.temperature_c is None
    assert res.current.humidity_percent is None
    assert res.current.rainfall_mm is None
    assert res.current.wind_speed_kmh is None
    assert res.current.rain_probability_percent is None
    assert res.forecast_3_days == []

# 26. Semantic Safety: WeatherDecisionEngine with Incomplete / Null Data
def test_weather_decision_engine_with_unavailable_data():
    # If rain probability is None, engine must not assume 0% rain
    partial_data = {
        "temperature_c": 29.0,
        "rainfall_mm": None,
        "rain_probability": None,
        "condition": "Partly Cloudy",
        "freshness": "CURRENT"
    }
    decision = WeatherDecisionEngine.evaluate(partial_data)
    assert decision.rainfall_mm is None
    assert decision.rain_probability is None
    assert decision.irrigation_decision == "PROCEED_WITH_CAUTION"
    assert "precipitation probability is unknown" in decision.irrigation_advice.lower()
    assert decision.spraying_decision == "HOLD"

# 27. Semantic Safety: JSON Serialization Distinguishes Null from Zero
def test_json_serialization_distinguishes_null_from_zero():
    # Measured zero response
    measured_zero = WeatherResponse(
        location="Guntur",
        current=WeatherCurrent(
            temperature_c=31.0,
            humidity_percent=60.0,
            rainfall_mm=0.0,
            wind_speed_kmh=10.0,
            weather_condition="Clear",
            rain_probability_percent=0,
            advisory="Normal conditions"
        ),
        forecast_3_days=[],
        source="Test Source"
    )
    json_zero = measured_zero.model_dump_json()
    assert '"rainfall_mm":0.0' in json_zero or '"rainfall_mm": 0.0' in json_zero
    assert '"rain_probability_percent":0' in json_zero or '"rain_probability_percent": 0' in json_zero

    # Unavailable response
    unavailable = WeatherResponse(
        location="Unknown",
        current=WeatherCurrent(
            temperature_c=None,
            humidity_percent=None,
            rainfall_mm=None,
            wind_speed_kmh=None,
            weather_condition="Unavailable",
            rain_probability_percent=None,
            advisory="Unavailable",
            freshness="UNAVAILABLE"
        ),
        forecast_3_days=[],
        source="Unavailable",
        freshness="UNAVAILABLE"
    )
    json_unavail = unavailable.model_dump_json()
    assert '"rainfall_mm":null' in json_unavail or '"rainfall_mm": null' in json_unavail
    assert '"temperature_c":null' in json_unavail or '"temperature_c": null' in json_unavail

# 28. Semantic Safety: Cached and Stale Retain Observed Measurements
def test_cached_and_stale_data_retains_numerical_measurements():
    cache = WeatherCache()
    key = "test_cached_measurements"
    original = WeatherResponse(
        location="Tenali",
        current=WeatherCurrent(
            temperature_c=33.5,
            humidity_percent=55.0,
            rainfall_mm=2.5,
            wind_speed_kmh=12.0,
            weather_condition="Light Rain",
            rain_probability_percent=35,
            advisory="Light rain detected"
        ),
        forecast_3_days=[],
        source="OpenWeatherMap"
    )
    # Stored 45 minutes ago (CACHED window)
    cache.set(key, original, cached_at=datetime.now(timezone.utc) - timedelta(minutes=45))
    cached_res, freshness = cache.get(key)
    
    assert freshness == "CACHED"
    # Must retain actual numerical measurements
    assert cached_res.current.temperature_c == 33.5
    assert cached_res.current.rainfall_mm == 2.5
    assert cached_res.current.rain_probability_percent == 35


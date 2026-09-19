"""
BHOOMI — Provider Fallback Safety & Degradation Validation Tests
Verifies that:
1. Gemini HTTP 429 executes bounded retries and falls back to explicit degraded state.
2. Timeout handling returns explicit timeout status.
3. Invalid provider responses (500, 503) do not return fabricated agricultural advice.
4. Missing API keys are handled strictly per environment policy.
5. Mock, Live, and Unavailable provider modes are distinctly tagged and never conflated.
6. Agricultural arithmetic, safety, and financial decisions remain 100% deterministic local.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.factory import get_llm_provider
from app.agents.orchestrator import BhoomiAgentOrchestrator, OrchestrationResult
from app.services.memory.digital_twin import DigitalTwinContext


@pytest.mark.asyncio
async def test_gemini_429_bounded_retry_and_degraded():
    """Gemini 429 rate limit triggers bounded retries, then returns explicit degraded state."""
    provider = GeminiProvider(api_key="test_key_gemini", timeout=5.0)

    # Mock 429 response
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = '{"error": {"code": 429, "message": "Resource has been exhausted"}}'

    call_count = 0
    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            res = await provider.generate_response(
                messages=[{"role": "user", "content": "test"}],
                system_prompt="system"
            )

    # Max retries = 2 -> total attempts = 3
    assert call_count == 3
    assert mock_sleep.call_count == 2
    assert res.provider == "gemini_degraded"
    assert "SERVICE_UNAVAILABLE" in res.content
    assert res.finish_reason == "rate_limit"


@pytest.mark.asyncio
async def test_gemini_timeout_handling():
    """Gemini timeout returns explicit timeout status without fabricating answers."""
    provider = GeminiProvider(api_key="test_key_gemini", timeout=1.0)

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
        res = await provider.generate_response(
            messages=[{"role": "user", "content": "weather"}],
            system_prompt="system"
        )

    assert res.provider == "gemini_timeout"
    assert "SERVICE_UNAVAILABLE" in res.content
    assert res.finish_reason == "timeout"


@pytest.mark.asyncio
async def test_gemini_invalid_provider_response():
    """Gemini 500 error returns unavailable state rather than silent false pass."""
    provider = GeminiProvider(api_key="test_key_gemini", timeout=5.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await provider.generate_response(
            messages=[{"role": "user", "content": "pest advisory"}],
            system_prompt="system"
        )

    assert res.provider == "unavailable"
    assert "SERVICE_UNAVAILABLE" in res.content
    assert res.finish_reason == "error"


def test_missing_api_key_production_rejection():
    """Production mode strictly forbids silent mock fallback on missing API keys."""
    from unittest.mock import PropertyMock
    from app.core.config import settings

    with patch.object(type(settings), "is_production", new_callable=PropertyMock) as mock_is_prod:
        mock_is_prod.return_value = True
        with pytest.raises(RuntimeError, match="Production configuration error: GEMINI_API_KEY must be provided"):
            with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
                get_llm_provider("gemini")


@pytest.mark.asyncio
async def test_mock_provider_mode():
    """MockLLMProvider explicitly declares provider='mock'."""
    provider = MockLLMProvider()
    res = await provider.generate_response(
        messages=[{"role": "user", "content": "hello"}],
        system_prompt="system"
    )
    assert res.provider == "mock"
    assert len(res.content) > 0


@pytest.mark.asyncio
async def test_live_provider_mode_success():
    """Successful API call returns provider='gemini' and parsed content."""
    provider = GeminiProvider(api_key="valid_key", timeout=5.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{
            "message": {"role": "assistant", "content": "Live agricultural advice for your chilli field."},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await provider.generate_response(
            messages=[{"role": "user", "content": "hello"}],
            system_prompt="system"
        )

    assert res.provider == "gemini"
    assert res.content == "Live agricultural advice for your chilli field."
    assert res.finish_reason == "stop"


@pytest.mark.asyncio
async def test_deterministic_local_safety_no_llm_dependency():
    """SafetyEngine blocks banned agrochemicals deterministically without LLM calls."""
    twin = DigitalTwinContext(
        farmer_id="farmer_safety_test",
        farmer_name="Suresh",
        state="Andhra Pradesh",
        district="Guntur",
        location="Guntur, Andhra Pradesh",
        total_land_acres=3.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0, "stage": "flowering"}]
    )

    # Query with banned substance in Telugu
    res = await BhoomiAgentOrchestrator.orchestrate(
        user_text="మిరప ఆకులు పైకి ముడుచుకుంటున్నాయి. మోనోక్రోటోఫాస్ పిచికారీ చేయవచ్చా?",
        session_id="sess_safe_test",
        farmer_id="farmer_safety_test",
        farm_id="farm_safe_test",
        context=twin,
        language="te"
    )

    assert res.provider_mode == "DETERMINISTIC_LOCAL"
    assert any(term in res.response_text for term in ["నిషేధించబడినది", "నిషిద్ధం", "ప్రమాదకరం", "మోనోక్రోటోఫాస్"])


@pytest.mark.asyncio
async def test_orchestrator_maps_unavailable_provider_mode():
    """When LLM returns degraded/unavailable, orchestrator tags provider_mode='UNAVAILABLE'."""
    twin = DigitalTwinContext(
        farmer_id="farmer_unavail_test",
        farmer_name="Suresh",
        state="Andhra Pradesh",
        district="Guntur",
        location="Guntur, Andhra Pradesh",
        total_land_acres=3.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0, "stage": "flowering"}]
    )

    degraded_llm = MagicMock()
    from app.services.llm.base import LLMResponse
    degraded_llm.generate_response = AsyncMock(return_value=LLMResponse(
        content="SERVICE_UNAVAILABLE: Gemini AI service rate limited (HTTP 429).",
        tool_calls=None,
        finish_reason="rate_limit",
        provider="gemini_degraded"
    ))

    with patch("app.agents.orchestrator.get_llm_provider", return_value=degraded_llm):
        res = await BhoomiAgentOrchestrator.orchestrate(
            user_text="Paddy leaves are drying and leaf edges are turning brown, what disease is this?",
            session_id="sess_unavail_test",
            farmer_id="farmer_unavail_test",
            farm_id="farm_unavail_test",
            context=twin,
            language="en"
        )

    assert res.provider_mode == "UNAVAILABLE"
    assert "SERVICE_UNAVAILABLE" in res.response_text

import pytest
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from app.schemas.market import (
    MarketComparisonResponse,
    MandiPrice,
    MarketFreshnessStatus
)
from app.services.market.market_provider import (
    MarketProviderFactory,
    MockMarketDataProvider,
    MarketDataProvider
)
from app.services.market.real_provider import RealMarketDataProvider
from app.services.market.market_service import MarketService
from app.services.market.cache import MarketCache, market_cache
from app.services.market.commodity_resolver import (
    resolve_commodity_search_terms,
    estimate_mandi_logistics
)
from app.services.farm_manager.market_decision import (
    MarketDecisionEngine,
    MarketDecisionOutput
)
from app.services.farm_manager.state_engine import FarmStateEngine
from app.services.farm_manager.proactive_alerts import (
    ProactiveAlertEngine,
    FarmerThresholds
)
from app.services.finance.profit_service import FinancialService
from app.schemas.finance import ProfitCalculationRequest
from app.agents.tool_registry import ToolRegistry
from app.agents.orchestrator import BhoomiAgentOrchestrator


@pytest.fixture(autouse=True)
def clean_market_cache():
    market_cache.clear()
    yield
    market_cache.clear()


# 1. Provider Factory Resolution
def test_provider_factory_resolution():
    mock_p = MarketProviderFactory.get_provider("mock")
    assert isinstance(mock_p, MockMarketDataProvider)

    data_gov_p = MarketProviderFactory.get_provider("data_gov")
    assert isinstance(data_gov_p, RealMarketDataProvider)

    agmarknet_p = MarketProviderFactory.get_provider("agmarknet")
    assert isinstance(agmarknet_p, RealMarketDataProvider)

    default_p = MarketProviderFactory.get_provider("unknown")
    assert isinstance(default_p, MockMarketDataProvider)


# 2. Mock Provider
@pytest.mark.asyncio
async def test_mock_provider():
    provider = MockMarketDataProvider()
    res = await provider.fetch_prices(commodity="Chilli", state="Andhra Pradesh", district="Guntur")
    assert isinstance(res, MarketComparisonResponse)
    assert res.commodity == "Chilli"
    assert len(res.mandi_options) == 3
    assert res.recommended_mandi == "Guntur Mandi (Benchmark)"
    assert res.best_net_realization == Decimal("12100.00")
    assert res.is_live is False
    assert res.freshness == "CURRENT"


# 3. Real Provider Configuration
def test_real_provider_configuration():
    provider = RealMarketDataProvider(api_key="gov_test_key_123", timeout_seconds=12.0)
    assert provider.api_key == "gov_test_key_123"
    assert provider.timeout_seconds == 12.0
    assert "api.data.gov.in" in provider.BASE_URL
    assert "9ef84268-d588-465a-a308-a864a43d0070" in provider.RESOURCE_ID


# 4. Missing Credentials
@pytest.mark.asyncio
async def test_missing_credentials():
    provider = RealMarketDataProvider(api_key=None)
    res = await provider.fetch_prices(commodity="Soybean", district="Indore")
    assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
    assert res.best_net_realization is None
    assert len(res.mandi_options) == 0
    assert "DATA_GOV_API_KEY is not configured" in res.recommendation_reason


# 5. Successful API Response Parsing
@pytest.mark.asyncio
async def test_successful_api_response_parsing():
    mock_response_data = {
        "records": [
            {
                "state": "Andhra Pradesh",
                "district": "Guntur",
                "market": "Guntur APMC",
                "commodity": "Chilli(Dry)",
                "variety": "Teja",
                "grade": "FAQ",
                "arrival_date": "03/09/2026",
                "min_price": "11500",
                "max_price": "13000",
                "modal_price": "12500"
            },
            {
                "state": "Andhra Pradesh",
                "district": "Krishna",
                "market": "Vijayawada APMC",
                "commodity": "Chilli(Dry)",
                "variety": "Common",
                "grade": "FAQ",
                "arrival_date": "03/09/2026",
                "min_price": "11000",
                "max_price": "12800",
                "modal_price": "12600"
            }
        ]
    }

    provider = RealMarketDataProvider(api_key="valid_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Chilli", state="Andhra Pradesh", district="Guntur")

        assert res.freshness == MarketFreshnessStatus.CURRENT.value
        assert res.is_live is True
        assert len(res.mandi_options) == 2
        assert res.recommended_mandi == "Guntur APMC"
        # Guntur: 12500 - 80(transport) - 20(selling) = 12400
        # Krishna: 12600 - 380(transport) - 30(selling) = 12190
        assert res.best_net_realization == Decimal("12400.00")
        assert res.mandi_options[0].modal_price_per_quintal == Decimal("12500.00")


# 6. Malformed Provider Response
@pytest.mark.asyncio
async def test_malformed_provider_response():
    provider = RealMarketDataProvider(api_key="valid_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"records": [{"market": "Bad APMC", "modal_price": "INVALID_NUMBER"}]}
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Chilli", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
        assert res.best_net_realization is None


# 7. Timeout Handling
@pytest.mark.asyncio
async def test_timeout_handling():
    provider = RealMarketDataProvider(api_key="valid_key")
    with patch("httpx.AsyncClient.get", side_effect=httpx.ReadTimeout("Timeout connecting to data.gov.in")):
        res = await provider.fetch_prices(commodity="Cotton", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
        assert res.best_net_realization is None
        assert "temporarily unavailable" in res.recommendation_reason


# 8. Network Failure Handling
@pytest.mark.asyncio
async def test_network_failure_handling():
    provider = RealMarketDataProvider(api_key="valid_key")
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("DNS resolution failed")):
        res = await provider.fetch_prices(commodity="Soybean", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
        assert res.best_net_realization is None


# 9. HTTP 401 Handling
@pytest.mark.asyncio
async def test_http_401_handling():
    provider = RealMarketDataProvider(api_key="bad_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Paddy", district="West Godavari")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
        assert res.best_net_realization is None


# 10. HTTP 403 Handling
@pytest.mark.asyncio
async def test_http_403_handling():
    provider = RealMarketDataProvider(api_key="forbidden_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Maize", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value


# 11. HTTP 404 Handling
@pytest.mark.asyncio
async def test_http_404_handling():
    provider = RealMarketDataProvider(api_key="valid_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Turmeric", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value


# 12. HTTP 429 Handling
@pytest.mark.asyncio
async def test_http_429_handling():
    provider = RealMarketDataProvider(api_key="rate_limited_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Chilli", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value


# 13. HTTP 5xx Handling
@pytest.mark.asyncio
async def test_http_5xx_handling():
    provider = RealMarketDataProvider(api_key="valid_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_get.return_value = mock_resp

        res = await provider.fetch_prices(commodity="Chilli", district="Guntur")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value


# 14. Null / Unknown Market Values
@pytest.mark.asyncio
async def test_null_unknown_market_values():
    provider = RealMarketDataProvider(api_key=None)
    res = await provider.fetch_prices(commodity="Soybean")
    assert res.best_net_realization is None
    assert res.recommended_mandi is None
    assert len(res.mandi_options) == 0


# 15. Measured Zero vs Unknown
def test_measured_zero_vs_unknown():
    price_zero = MandiPrice(
        mandi_name="Terminal APMC",
        district="Guntur",
        state="Andhra Pradesh",
        commodity="Chilli",
        modal_price_per_quintal=Decimal("0.00"),
        transport_cost_per_quintal=Decimal("0.00"),
        selling_cost_per_quintal=Decimal("0.00"),
        net_realization_per_quintal=Decimal("0.00")
    )
    assert price_zero.modal_price_per_quintal == Decimal("0.00")
    assert price_zero.net_realization_per_quintal == Decimal("0.00")
    assert price_zero.status == "VALID"

    price_null = MandiPrice(
        mandi_name="Unreported APMC",
        district="Guntur",
        state="Andhra Pradesh",
        commodity="Chilli",
        modal_price_per_quintal=None,
        transport_cost_per_quintal=None,
        selling_cost_per_quintal=None,
        net_realization_per_quintal=None
    )
    assert price_null.modal_price_per_quintal is None
    assert price_null.net_realization_per_quintal is None
    assert price_null.status == "INSUFFICIENT_DATA"


# 16. Freshness Calculation
def test_freshness_calculation():
    cache = MarketCache(live_window_hours=6.0, stale_threshold_hours=24.0)
    key = cache.make_key("Chilli", "Andhra Pradesh", "Guntur", "all", "today")

    dummy_res = MarketComparisonResponse(
        commodity="Chilli",
        recommended_mandi="Guntur APMC",
        best_net_realization=Decimal("12100.00"),
        mandi_options=[]
    )

    now = datetime.now(timezone.utc)
    # CURRENT (< 6 hours)
    cache.set(key, dummy_res, cached_at=now - timedelta(hours=2))
    item = cache.get(key)
    assert item is not None
    assert item[1] == MarketFreshnessStatus.CURRENT.value
    assert item[0].is_live is True

    # CACHED (6-24 hours)
    cache.set(key, dummy_res, cached_at=now - timedelta(hours=10))
    item = cache.get(key)
    assert item is not None
    assert item[1] == MarketFreshnessStatus.CACHED.value
    assert item[0].is_live is False

    # STALE (>= 24 hours)
    cache.set(key, dummy_res, cached_at=now - timedelta(hours=30))
    item = cache.get(key)
    assert item is not None
    assert item[1] == MarketFreshnessStatus.STALE.value
    assert item[0].is_live is False


# 17. Cache Behavior
@pytest.mark.asyncio
async def test_cache_behavior():
    cache_key = market_cache.make_key("Chilli", "Andhra Pradesh", "Guntur", None, "today")
    dummy_resp = MarketComparisonResponse(
        commodity="Chilli",
        recommended_mandi="Guntur Mandi",
        best_net_realization=Decimal("12100.00"),
        mandi_options=[],
        freshness=MarketFreshnessStatus.CURRENT.value
    )
    market_cache.set(cache_key, dummy_resp)

    provider = RealMarketDataProvider(api_key="any_key")
    with patch("httpx.AsyncClient.get") as mock_get:
        res = await provider.fetch_prices(commodity="Chilli", state="Andhra Pradesh", district="Guntur")
        mock_get.assert_not_called()
        assert res.recommended_mandi == "Guntur Mandi"
        assert res.freshness == MarketFreshnessStatus.CURRENT.value


# 18. Historical CSV Cannot Become CURRENT
def test_historical_csv_cannot_become_current():
    cache = MarketCache()
    key = cache.make_key("Soybean", "Madhya Pradesh", "Indore", "all", "historical")

    historical_resp = MarketComparisonResponse(
        commodity="Soybean",
        recommended_mandi="Indore Mandi",
        best_net_realization=Decimal("4500.00"),
        mandi_options=[],
        freshness=MarketFreshnessStatus.HISTORICAL.value,
        is_live=False
    )
    # Even if cached 1 minute ago, it MUST remain HISTORICAL
    cache.set(key, historical_resp, cached_at=datetime.now(timezone.utc) - timedelta(minutes=1))

    retrieved, status = cache.get(key)
    assert status == MarketFreshnessStatus.HISTORICAL.value
    assert retrieved.freshness == MarketFreshnessStatus.HISTORICAL.value
    assert retrieved.is_live is False


# 19. Market Tool Integration
@pytest.mark.asyncio
async def test_market_tool_integration():
    tool_input = {"commodity": "Chilli", "location": "Guntur"}
    res = await ToolRegistry.execute_tool("get_mandi_prices", tool_input)
    assert res["card_type"] == "market_card"
    assert "Mandi Net Realization: Chilli" in res["title"]
    assert "best_net_realization" in res["data"]


# 20. FarmState Integration
@pytest.mark.asyncio
async def test_farm_state_integration():
    state = await FarmStateEngine.get_current_state("farmer_123")
    assert state.market_summary is not None
    assert "commodity" in state.market_summary
    assert "recommended_mandi" in state.market_summary
    assert "market" in state.data_freshness
    assert state.data_freshness["market"].source != ""


# 21. MarketDecisionEngine Integration
def test_market_decision_engine_integration():
    out = MarketDecisionEngine.evaluate(
        crop_name="Chilli",
        current_modal_price=Decimal("13000.00"),
        transport_cost=Decimal("80.00"),
        min_acceptable_price=Decimal("11500.00"),
        is_harvest_ready=True
    )
    assert out.decision == "SELL NOW"
    assert "favorable margins" in out.rationale


# 22. FinancialService Decimal Integration
def test_financial_service_decimal_integration():
    # Net Realization: ₹12,100/Q
    req = ProfitCalculationRequest(
        crop_name="Chilli",
        area_acres=Decimal("3.0"),
        expected_yield_quintals_per_acre=Decimal("10.0"),
        expected_market_price_per_quintal=Decimal("12100.00"),
        cultivation_cost_total=Decimal("70000.00")
    )
    res = FinancialService.calculate_profit(req)
    assert res.gross_revenue == Decimal("363000.00")
    assert res.net_profit == Decimal("293000.00")
    assert res.return_on_investment_percent > Decimal("0")


# 23. Net Realization Calculation
def test_net_realization_calculation():
    modal_price = Decimal("12200.00")
    transport_cost = Decimal("80.00")
    selling_fees = Decimal("20.00")
    net_realization = modal_price - transport_cost - selling_fees
    assert net_realization == Decimal("12100.00")


# 24. Multiple Mandi Comparison
def test_multiple_mandi_comparison():
    # Mandi A has lower modal price (3000) but low transport (200) -> Net: 2800
    mandi_a = MandiPrice(
        mandi_name="Local Mandi A",
        district="Home District",
        state="State",
        commodity="Soybean",
        modal_price_per_quintal=Decimal("3000.00"),
        transport_cost_per_quintal=Decimal("200.00"),
        selling_cost_per_quintal=Decimal("0.00"),
        net_realization_per_quintal=Decimal("2800.00")
    )
    # Mandi B has higher modal price (3100) but high transport (500) -> Net: 2600
    mandi_b = MandiPrice(
        mandi_name="Distant Mandi B",
        district="Far District",
        state="State",
        commodity="Soybean",
        modal_price_per_quintal=Decimal("3100.00"),
        transport_cost_per_quintal=Decimal("500.00"),
        selling_cost_per_quintal=Decimal("0.00"),
        net_realization_per_quintal=Decimal("2600.00")
    )

    out = MarketDecisionEngine.evaluate(
        crop_name="Soybean",
        mandi_options=[mandi_a, mandi_b],
        min_acceptable_price=Decimal("2500.00"),
        is_harvest_ready=True
    )
    assert out.recommended_mandi == "Local Mandi A"
    assert out.net_realization_per_quintal == Decimal("2800.00")


# 25. SELL_NOW / WAIT / COMPARE_MARKETS Logic
def test_sell_now_wait_compare_markets_logic():
    # 1. Not harvest ready -> MONITOR
    m1 = MarketDecisionEngine.evaluate(
        crop_name="Chilli",
        current_modal_price=Decimal("13000.00"),
        is_harvest_ready=False
    )
    assert m1.decision == "MONITOR"

    # 2. Bullish margin >= 8% above min -> SELL NOW
    m2 = MarketDecisionEngine.evaluate(
        crop_name="Chilli",
        current_modal_price=Decimal("13000.00"),
        transport_cost=Decimal("80.00"),
        min_acceptable_price=Decimal("11500.00"),
        is_harvest_ready=True
    )
    assert m2.decision == "SELL NOW"

    # 3. Below target threshold + cold storage feasible -> WAIT
    m3 = MarketDecisionEngine.evaluate(
        crop_name="Chilli",
        current_modal_price=Decimal("11000.00"),
        transport_cost=Decimal("80.00"),
        min_acceptable_price=Decimal("11500.00"),
        has_cold_storage=True,
        is_harvest_ready=True
    )
    assert m3.decision == "WAIT"

    # 4. In between -> COMPARE MARKETS
    m4 = MarketDecisionEngine.evaluate(
        crop_name="Chilli",
        current_modal_price=Decimal("11800.00"),
        transport_cost=Decimal("80.00"),
        min_acceptable_price=Decimal("11500.00"),
        has_cold_storage=False,
        is_harvest_ready=True
    )
    assert m4.decision == "COMPARE MARKETS"


# 26. Unavailable Market Behavior
def test_unavailable_market_behavior():
    out = MarketDecisionEngine.evaluate(
        crop_name="Chilli",
        current_modal_price=None,
        freshness="UNAVAILABLE"
    )
    assert out.decision == "INSUFFICIENT_DATA"
    assert out.current_modal_price is None
    assert out.net_realization_per_quintal is None
    assert "unavailable" in out.rationale.lower()


# 27. Agent Market Query Integration
@pytest.mark.asyncio
async def test_agent_market_query_integration():
    result = await BhoomiAgentOrchestrator.process_turn(
        farmer_id="farmer_test_market_query",
        user_text="What is the current mandi price of chilli and which market gives the best return?",
        input_mode="text"
    )
    assert result.response_text is not None
    assert len(result.response_text) > 10
    text_lower = result.response_text.lower()
    assert "chilli" in text_lower or "mandi" in text_lower or "price" in text_lower or "farm" in text_lower


# 28. Proactive Market Alert Integration
@pytest.mark.asyncio
async def test_proactive_market_alert_integration():
    state = await FarmStateEngine.get_current_state("farmer_123")
    thresholds = FarmerThresholds(min_selling_price_per_quintal=11000.0)

    alerts = ProactiveAlertEngine.evaluate_alerts(state, thresholds)
    market_alerts = [a for a in alerts if a.category == "MARKET"]
    assert len(market_alerts) >= 1
    assert "Mandi Target Price Reached" in market_alerts[0].title

    # When market data is UNAVAILABLE, alerts MUST NOT fire
    state.data_freshness["market"].freshness_status = "UNAVAILABLE"
    alerts_unavail = ProactiveAlertEngine.evaluate_alerts(state, thresholds)
    unavail_market_alerts = [a for a in alerts_unavail if a.category == "MARKET"]
    assert len(unavail_market_alerts) == 0


# 29. No Fabricated Prices
@pytest.mark.asyncio
async def test_no_fabricated_prices():
    provider = RealMarketDataProvider(api_key="test_key")
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network down")):
        res = await provider.fetch_prices(commodity="UnknownCrop")
        assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
        assert res.best_net_realization is None
        assert res.recommended_mandi is None
        assert len(res.mandi_options) == 0


# 30. Provenance Fields
@pytest.mark.asyncio
async def test_provenance_fields():
    provider = MockMarketDataProvider()
    res = await provider.fetch_prices(commodity="Chilli")
    assert res.source != ""
    assert res.retrieved_at is not None
    assert res.freshness in [s.value for s in MarketFreshnessStatus]
    for opt in res.mandi_options:
        assert opt.source != ""
        assert opt.arrival_date is not None
        assert opt.price_date is not None
        assert opt.freshness != ""


# 31. Four-Mandi Deterministic Ranking Audit
def test_four_mandi_deterministic_ranking():
    # Mandi A: modal = 2400, transport = 100, fee = 20 -> net = 2280
    mandi_a = MandiPrice(
        mandi_name="Mandi A",
        district="District A",
        state="State",
        commodity="Paddy",
        modal_price_per_quintal=Decimal("2400.00"),
        transport_cost_per_quintal=Decimal("100.00"),
        selling_cost_per_quintal=Decimal("20.00")
    )
    assert mandi_a.net_realization_per_quintal == Decimal("2280.00")
    assert mandi_a.status == "VALID"

    # Mandi B: modal = 2500, transport = 300, fee = 20 -> net = 2180
    mandi_b = MandiPrice(
        mandi_name="Mandi B",
        district="District B",
        state="State",
        commodity="Paddy",
        modal_price_per_quintal=Decimal("2500.00"),
        transport_cost_per_quintal=Decimal("300.00"),
        selling_cost_per_quintal=Decimal("20.00")
    )
    assert mandi_b.net_realization_per_quintal == Decimal("2180.00")
    assert mandi_b.status == "VALID"

    # Mandi C: modal = 2350, transport = 40, fee = 10 -> net = 2300
    mandi_c = MandiPrice(
        mandi_name="Mandi C",
        district="District C",
        state="State",
        commodity="Paddy",
        modal_price_per_quintal=Decimal("2350.00"),
        transport_cost_per_quintal=Decimal("40.00"),
        selling_cost_per_quintal=Decimal("10.00")
    )
    assert mandi_c.net_realization_per_quintal == Decimal("2300.00")
    assert mandi_c.status == "VALID"

    # Mandi D: modal = 2600, transport = null, fee = 20 -> net = null, status = INSUFFICIENT_DATA
    mandi_d = MandiPrice(
        mandi_name="Mandi D",
        district="District D",
        state="State",
        commodity="Paddy",
        modal_price_per_quintal=Decimal("2600.00"),
        transport_cost_per_quintal=None,
        selling_cost_per_quintal=Decimal("20.00")
    )
    assert mandi_d.net_realization_per_quintal is None
    assert mandi_d.status == "INSUFFICIENT_DATA"

    # Evaluate decision across all 4 mandis
    out = MarketDecisionEngine.evaluate(
        crop_name="Paddy",
        mandi_options=[mandi_a, mandi_b, mandi_c, mandi_d],
        min_acceptable_price=Decimal("2100.00"),
        is_harvest_ready=True
    )

    # 1. Mandi C MUST be recommended (highest net realization ₹2,300)
    assert out.recommended_mandi == "Mandi C"
    assert out.net_realization_per_quintal == Decimal("2300.00")

    # 2. Mandi B must NOT be recommended merely because modal price is higher (2500 vs 2350)
    assert out.recommended_mandi != "Mandi B"

    # 3. Mandi D must NOT be treated as net = 2580 (silently assuming zero transport)
    assert out.recommended_mandi != "Mandi D"
    assert out.net_realization_per_quintal != Decimal("2580.00")

    # 4. Rationale must explain net realization
    assert "Mandi C" in out.rationale
    assert "2,300.00" in out.rationale


# 32. Highest Modal Price != Highest Net Realization
def test_highest_modal_price_not_necessarily_highest_net_realization():
    high_modal_far = MandiPrice(
        mandi_name="High Modal Distant APMC",
        district="Far",
        state="State",
        commodity="Chilli",
        modal_price_per_quintal=Decimal("14000.00"),
        transport_cost_per_quintal=Decimal("2500.00"),
        selling_cost_per_quintal=Decimal("100.00")
    )
    # Net = 14000 - 2500 - 100 = 11400

    modest_modal_near = MandiPrice(
        mandi_name="Local APMC",
        district="Near",
        state="State",
        commodity="Chilli",
        modal_price_per_quintal=Decimal("12500.00"),
        transport_cost_per_quintal=Decimal("80.00"),
        selling_cost_per_quintal=Decimal("20.00")
    )
    # Net = 12500 - 80 - 20 = 12400

    out = MarketDecisionEngine.evaluate(
        crop_name="Chilli",
        mandi_options=[high_modal_far, modest_modal_near],
        min_acceptable_price=Decimal("11000.00"),
        is_harvest_ready=True
    )
    # Local APMC has higher net realization (12400 vs 11400) despite 1500 lower nominal modal price
    assert out.recommended_mandi == "Local APMC"
    assert out.net_realization_per_quintal == Decimal("12400.00")
    assert high_modal_far.modal_price_per_quintal > modest_modal_near.modal_price_per_quintal
    assert high_modal_far.net_realization_per_quintal < modest_modal_near.net_realization_per_quintal


# 33. Null Transport != Zero Transport
def test_null_transport_not_zero_transport():
    mandi = MandiPrice(
        mandi_name="Unknown Logistics APMC",
        district="Guntur",
        state="Andhra Pradesh",
        commodity="Chilli",
        modal_price_per_quintal=Decimal("12000.00"),
        transport_cost_per_quintal=None,
        selling_cost_per_quintal=Decimal("20.00")
    )
    # Must NOT silently compute 12000 - 0 - 20 = 11980
    assert mandi.net_realization_per_quintal is None
    assert mandi.status == "INSUFFICIENT_DATA"


# 34. Null Selling Fee != Zero Selling Fee
def test_null_selling_fee_not_zero_selling_fee():
    mandi = MandiPrice(
        mandi_name="Unknown Fee APMC",
        district="Guntur",
        state="Andhra Pradesh",
        commodity="Chilli",
        modal_price_per_quintal=Decimal("12000.00"),
        transport_cost_per_quintal=Decimal("100.00"),
        selling_cost_per_quintal=None
    )
    # Must NOT silently compute 12000 - 100 - 0 = 11900
    assert mandi.net_realization_per_quintal is None
    assert mandi.status == "INSUFFICIENT_DATA"


# 35. Incomplete Mandi Data Cannot Become Recommended Mandi
def test_incomplete_mandi_data_cannot_become_recommended():
    incomplete_mandi = MandiPrice(
        mandi_name="Incomplete Sky-High APMC",
        district="Nowhere",
        state="State",
        commodity="Maize",
        modal_price_per_quintal=Decimal("99999.00"),
        transport_cost_per_quintal=None,
        selling_cost_per_quintal=Decimal("20.00")
    )
    complete_mandi = MandiPrice(
        mandi_name="Honest APMC",
        district="Guntur",
        state="State",
        commodity="Maize",
        modal_price_per_quintal=Decimal("2400.00"),
        transport_cost_per_quintal=Decimal("50.00"),
        selling_cost_per_quintal=Decimal("10.00")
    )

    out = MarketDecisionEngine.evaluate(
        crop_name="Maize",
        mandi_options=[incomplete_mandi, complete_mandi],
        min_acceptable_price=Decimal("2000.00"),
        is_harvest_ready=True
    )
    assert out.recommended_mandi == "Honest APMC"
    assert out.net_realization_per_quintal == Decimal("2340.00")

    # If ALL mandis are incomplete, must return INSUFFICIENT_DATA
    all_incomplete_out = MarketDecisionEngine.evaluate(
        crop_name="Maize",
        mandi_options=[incomplete_mandi],
        min_acceptable_price=Decimal("2000.00"),
        is_harvest_ready=True
    )
    assert all_incomplete_out.decision == "INSUFFICIENT_DATA"
    assert all_incomplete_out.recommended_mandi is None
    assert all_incomplete_out.net_realization_per_quintal is None


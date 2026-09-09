import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
import httpx
from app.schemas.market import (
    MarketComparisonResponse,
    MandiPrice,
    MarketFreshnessStatus
)
from app.services.market.market_provider import MarketDataProvider
from app.services.market.commodity_resolver import (
    resolve_commodity_search_terms,
    estimate_mandi_logistics
)
from app.services.market.cache import market_cache
from app.core.exceptions import BhoomiException

logger = logging.getLogger(__name__)

class RealMarketDataProvider(MarketDataProvider):
    """
    Production Real Market Data Provider connecting to official Government of India
    Agmarknet wholesale mandi price feeds via data.gov.in (Resource 9ef84268-d588-465a-a308-a864a43d0070).
    Performs deterministic Net Realization calculations:
      Net Realization = Modal Price - Transport Cost - Mandi Handling/Selling Fees
    Enforces strict caching, data provenance, and fallback isolation with explicit null values when unavailable.
    """
    RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
    BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: float = 15.0
    ):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def fetch_prices(
        self,
        commodity: str = "Chilli",
        state: str = "Andhra Pradesh",
        district: str = "Guntur",
        market_name: Optional[str] = None
    ) -> MarketComparisonResponse:
        now_utc = datetime.now(timezone.utc)
        cache_key = market_cache.make_key(
            commodity=commodity,
            state=state,
            district=district,
            market=market_name,
            target_date="today"
        )

        # 1. Check Fresh Cache First (Avoid redundant API calls)
        cached_item = market_cache.get(cache_key)
        if cached_item:
            cached_resp, freshness = cached_item
            if freshness == MarketFreshnessStatus.CURRENT.value:
                logger.info("Serving CURRENT market data from cache for %s in %s", commodity, district)
                return cached_resp

        # 2. Check for missing/placeholder API key
        if not self.api_key or self.api_key.startswith("your_"):
            logger.warning("DATA_GOV_API_KEY is not configured or placeholder detected.")
            if cached_item:
                return cached_item[0]
            return self._build_unavailable_response(
                commodity=commodity,
                state=state,
                district=district,
                reason="DATA_GOV_API_KEY is not configured on the server."
            )

        # 3. Query Official data.gov.in Agmarknet API
        headers = {"User-Agent": "BhoomiFarmManager/2.0"}
        search_terms = resolve_commodity_search_terms(commodity)

        try:
            records = []
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
                for term in search_terms:
                    params = {
                        "api-key": self.api_key,
                        "format": "json",
                        "limit": 15,
                        "filters[state]": state,
                        "filters[commodity]": term
                    }
                    if district and district.lower() != "all":
                        params["filters[district]"] = district
                    if market_name:
                        params["filters[market]"] = market_name

                    resp = await client.get(self.BASE_URL, params=params)

                    if resp.status_code in (401, 403):
                        raise BhoomiException("data.gov.in authentication failed. Verify DATA_GOV_API_KEY.", status_code=401)
                    elif resp.status_code == 404:
                        raise BhoomiException("data.gov.in resource not found.", status_code=404)
                    elif resp.status_code == 429:
                        raise BhoomiException("data.gov.in rate limit exceeded.", status_code=429)
                    elif resp.status_code >= 500:
                        raise BhoomiException("data.gov.in upstream server error.", status_code=502)
                    elif resp.status_code != 200:
                        raise BhoomiException(f"data.gov.in error status {resp.status_code}.", status_code=resp.status_code)

                    payload = resp.json()
                    term_records = payload.get("records", [])
                    if term_records:
                        records.extend(term_records)
                        break  # Found matching records for primary term

                # If district query yielded no records, query state-level nearby records for comparison
                if not records and district and district.lower() != "all":
                    fallback_params = {
                        "api-key": self.api_key,
                        "format": "json",
                        "limit": 10,
                        "filters[state]": state,
                        "filters[commodity]": search_terms[0]
                    }
                    fb_resp = await client.get(self.BASE_URL, params=fallback_params)
                    if fb_resp.status_code == 200:
                        records = fb_resp.json().get("records", [])

            if not records:
                logger.warning("No live Agmarknet records found for %s in %s, %s", commodity, district, state)
                if cached_item:
                    return cached_item[0]
                return self._build_unavailable_response(
                    commodity=commodity,
                    state=state,
                    district=district,
                    reason=f"No daily market arrivals currently reported for {commodity} in {district}."
                )

            # 4. Parse Records into MandiPrice with Deterministic Net Realization
            mandi_options: List[MandiPrice] = []
            for rec in records:
                m_name = str(rec.get("market", "APMC Mandi"))
                m_dist = str(rec.get("district", district))
                m_state = str(rec.get("state", state))
                var_name = str(rec.get("variety", "Standard"))
                grade_name = str(rec.get("grade", "FAQ"))
                arr_date_str = str(rec.get("arrival_date", ""))

                try:
                    modal_val = Decimal(str(rec.get("modal_price", 0)))
                    min_val = Decimal(str(rec.get("min_price", modal_val)))
                    max_val = Decimal(str(rec.get("max_price", modal_val)))
                except Exception:
                    continue

                dist_km, trans_cost, sell_cost = estimate_mandi_logistics(
                    farmer_district=district,
                    mandi_district=m_dist,
                    mandi_name=m_name
                )
                net_real = modal_val - trans_cost - sell_cost

                # Parse arrival date into date object if possible
                p_date = None
                if arr_date_str:
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            p_date = datetime.strptime(arr_date_str, fmt).date()
                            break
                        except ValueError:
                            pass

                mandi_options.append(
                    MandiPrice(
                        mandi_name=m_name,
                        district=m_dist,
                        state=m_state,
                        commodity=commodity,
                        variety=var_name,
                        grade=grade_name,
                        min_price_per_quintal=min_val,
                        max_price_per_quintal=max_val,
                        modal_price_per_quintal=modal_val,
                        distance_km=dist_km,
                        transport_cost_per_quintal=trans_cost,
                        selling_cost_per_quintal=sell_cost,
                        net_realization_per_quintal=net_real,
                        arrival_date=arr_date_str,
                        price_date=p_date or date.today(),
                        source="AGMARKNET / data.gov.in",
                        retrieved_at=now_utc.isoformat(),
                        freshness=MarketFreshnessStatus.CURRENT.value,
                        is_live=True
                    )
                )

            if not mandi_options:
                if cached_item:
                    return cached_item[0]
                return self._build_unavailable_response(
                    commodity=commodity,
                    state=state,
                    district=district,
                    reason="Could not extract valid numerical prices from provider."
                )

            # 5. Rank by Highest Net Realization (Not merely nominal modal price)
            valid_options = [o for o in mandi_options if o.status == "VALID" and o.net_realization_per_quintal is not None]
            if not valid_options:
                if cached_item:
                    return cached_item[0]
                return self._build_unavailable_response(
                    commodity=commodity,
                    state=state,
                    district=district,
                    reason="No mandi options had complete economic cost inputs (transport and fees)."
                )

            best_option = max(valid_options, key=lambda x: x.net_realization_per_quintal)
            reason = self._build_comparison_rationale(best_option, mandi_options)

            response = MarketComparisonResponse(
                commodity=commodity,
                variety=best_option.variety,
                state=state,
                district=district,
                recommended_mandi=best_option.mandi_name,
                best_net_realization=best_option.net_realization_per_quintal,
                mandi_options=mandi_options,
                recommendation_reason=reason,
                source="AGMARKNET / data.gov.in Official Price Feed",
                freshness=MarketFreshnessStatus.CURRENT.value,
                retrieved_at=now_utc.isoformat(),
                is_live=True
            )

            # Store in cache
            market_cache.set(cache_key, response)
            return response

        except Exception as e:
            logger.error("RealMarketDataProvider query failed: %s (%s)", type(e).__name__, str(e))
            # Fall back to cache if available
            if cached_item:
                cached_resp, freshness = cached_item
                logger.warning("Serving %s market data following provider error", freshness)
                return cached_resp

            return self._build_unavailable_response(
                commodity=commodity,
                state=state,
                district=district,
                reason=f"Live mandi price service temporarily unavailable ({type(e).__name__}). No prior cache exists."
            )

    def _build_comparison_rationale(
        self,
        best: MandiPrice,
        options: List[MandiPrice]
    ) -> str:
        """Constructs plain-language explanation of why the recommended mandi yields highest net returns."""
        valid_options = [o for o in options if o.status == "VALID" and o.net_realization_per_quintal is not None]
        highest_nominal = max(valid_options, key=lambda x: x.modal_price_per_quintal or Decimal("0")) if valid_options else best

        if highest_nominal.mandi_name != best.mandi_name:
            return (
                f"Even though {highest_nominal.mandi_name} lists a higher nominal modal price (₹{highest_nominal.modal_price_per_quintal:,.2f}/Q), "
                f"{best.mandi_name} provides the highest estimated net realization of ₹{best.net_realization_per_quintal:,.2f}/Q "
                f"after ₹{best.transport_cost_per_quintal:,.2f}/Q transport and ₹{best.selling_cost_per_quintal:,.2f}/Q selling costs "
                f"(vs ₹{highest_nominal.transport_cost_per_quintal:,.2f}/Q transport at {highest_nominal.mandi_name})."
            )
        else:
            return (
                f"{best.mandi_name} provides the highest estimated net realization of ₹{best.net_realization_per_quintal:,.2f}/Q "
                f"after ₹{best.transport_cost_per_quintal:,.2f}/Q transport and ₹{best.selling_cost_per_quintal:,.2f}/Q selling costs."
            )

    def _build_unavailable_response(
        self,
        commodity: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
        reason: str = "Market data unavailable."
    ) -> MarketComparisonResponse:
        """Returns structured UNAVAILABLE response with explicit null prices."""
        now_utc = datetime.now(timezone.utc)
        return MarketComparisonResponse(
            commodity=commodity,
            state=state,
            district=district,
            recommended_mandi=None,
            best_net_realization=None,
            mandi_options=[],
            recommendation_reason=f"Current market prices are unavailable. {reason} Please verify rates with your local APMC secretary.",
            source="Unavailable",
            freshness=MarketFreshnessStatus.UNAVAILABLE.value,
            retrieved_at=now_utc.isoformat(),
            is_live=False
        )

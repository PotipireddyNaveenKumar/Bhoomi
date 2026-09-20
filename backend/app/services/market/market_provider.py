import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timezone
from decimal import Decimal
from app.core.config import settings
from app.schemas.market import MarketComparisonResponse, MandiPrice, MarketFreshnessStatus

logger = logging.getLogger(__name__)

class MarketDataProvider(ABC):
    @abstractmethod
    async def fetch_prices(
        self,
        commodity: str,
        state: str,
        district: str,
        market_name: Optional[str] = None
    ) -> MarketComparisonResponse:
        pass

class MockMarketDataProvider(MarketDataProvider):
    """
    Deterministic mock market data provider.
    Used exclusively for automated unit testing, CI/CD, and explicit offline demonstration.
    All outputs are strictly labeled as DEMO / SYNTHETIC.
    """
    async def fetch_prices(
        self,
        commodity: str = "Chilli",
        state: str = "Andhra Pradesh",
        district: str = "Guntur",
        market_name: Optional[str] = None
    ) -> MarketComparisonResponse:
        today = date.today()
        now_utc = datetime.now(timezone.utc).isoformat()
        
        options = [
            MandiPrice(
                mandi_name="Guntur Mandi (Benchmark)",
                district="Guntur",
                state="Andhra Pradesh",
                commodity=commodity,
                variety="Teja Quality",
                min_price_per_quintal=Decimal("11000.00"),
                max_price_per_quintal=Decimal("13200.00"),
                modal_price_per_quintal=Decimal("12200.00"),
                distance_km=Decimal("15.0"),
                transport_cost_per_quintal=Decimal("80.00"),
                selling_cost_per_quintal=Decimal("20.00"),
                net_realization_per_quintal=Decimal("12100.00"),
                arrival_date=today.strftime("%d/%m/%Y"),
                price_date=today,
                source="Demo / Synthetic Benchmark (Offline Demonstration)",
                retrieved_at=now_utc,
                freshness=MarketFreshnessStatus.DEMO.value,
                is_live=False,
                is_synthetic=True,
            ),
            MandiPrice(
                mandi_name="Khammam Mandi",
                district="Khammam",
                state="Telangana",
                commodity=commodity,
                variety="Teja / Fatki",
                min_price_per_quintal=Decimal("11500.00"),
                max_price_per_quintal=Decimal("12800.00"),
                modal_price_per_quintal=Decimal("12400.00"),
                distance_km=Decimal("110.0"),
                transport_cost_per_quintal=Decimal("380.00"),
                selling_cost_per_quintal=Decimal("30.00"),
                net_realization_per_quintal=Decimal("11990.00"),
                arrival_date=today.strftime("%d/%m/%Y"),
                price_date=today,
                source="Demo / Synthetic Benchmark (Offline Demonstration)",
                retrieved_at=now_utc,
                freshness=MarketFreshnessStatus.DEMO.value,
                is_live=False,
                is_synthetic=True,
            ),
            MandiPrice(
                mandi_name="Warangal Mandi",
                district="Warangal",
                state="Telangana",
                commodity=commodity,
                variety="Grade A",
                min_price_per_quintal=Decimal("10800.00"),
                max_price_per_quintal=Decimal("12500.00"),
                modal_price_per_quintal=Decimal("11900.00"),
                distance_km=Decimal("180.0"),
                transport_cost_per_quintal=Decimal("520.00"),
                selling_cost_per_quintal=Decimal("40.00"),
                net_realization_per_quintal=Decimal("11340.00"),
                arrival_date=today.strftime("%d/%m/%Y"),
                price_date=today,
                source="Demo / Synthetic Benchmark (Offline Demonstration)",
                retrieved_at=now_utc,
                freshness=MarketFreshnessStatus.DEMO.value,
                is_live=False,
                is_synthetic=True,
            ),
        ]

        best_option = max(options, key=lambda x: x.net_realization_per_quintal)
        reason = (
            f"[DEMO MODE] Synthetic benchmark data for demonstration only. "
            f"Even though Khammam Mandi displays a slightly higher nominal modal price (₹12,400), "
            f"{best_option.mandi_name} yields the highest Net Realization of ₹{best_option.net_realization_per_quintal:,.2f}/quintal "
            f"after accounting for transport costs (₹{best_option.transport_cost_per_quintal}/q vs ₹380/q)."
        )

        return MarketComparisonResponse(
            commodity=commodity,
            state=state,
            district=district,
            recommended_mandi=best_option.mandi_name,
            best_net_realization=best_option.net_realization_per_quintal,
            mandi_options=options,
            recommendation_reason=reason,
            source="Demo / Synthetic Benchmark (Offline Demonstration)",
            freshness=MarketFreshnessStatus.DEMO.value,
            retrieved_at=now_utc,
            is_live=False,
            is_synthetic=True,
            provider_status="DEMO",
        )

class MarketProviderFactory:
    """
    Factory resolving active MarketDataProvider.
    Strictly forbids mock market data in production (DEMO_MODE=False).
    Preserves MockMarketDataProvider only for explicit demo mode and isolated tests.
    """
    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> MarketDataProvider:
        from app.services.market.real_provider import RealMarketDataProvider

        is_prod = settings.APP_ENV in ["production", "staging"] or getattr(settings, "is_production", False)
        
        target_name = (
            provider_name or
            os.environ.get("MARKET_PROVIDER") or
            settings.MARKET_PROVIDER or
            ("data_gov" if is_prod else "mock")
        ).lower().strip()

        # In production or staging, NEVER use MockMarketDataProvider
        if is_prod:
            if target_name == "mock":
                logger.warning("MockMarketDataProvider strictly forbidden in %s; activating RealMarketDataProvider.", settings.APP_ENV)
            api_key = os.environ.get("DATA_GOV_API_KEY") or settings.DATA_GOV_API_KEY
            return RealMarketDataProvider(api_key=api_key)

        # In non-production, return RealMarketDataProvider when requested
        if target_name in ("data_gov", "real", "agmarknet"):
            api_key = os.environ.get("DATA_GOV_API_KEY") or settings.DATA_GOV_API_KEY
            return RealMarketDataProvider(api_key=api_key)

        return MockMarketDataProvider()

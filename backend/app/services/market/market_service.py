from decimal import Decimal
from typing import Optional, List
from app.schemas.market import MarketComparisonResponse, MandiPrice
from app.services.market.market_provider import MarketProviderFactory

class MarketService:
    """
    Market Mandi Intelligence Service.
    Calculates true Net Realization per quintal:
    Net Realization = Modal Price - Transport Cost - Other Mandi Selling Costs
    Dispatches to configured MarketDataProvider (RealMarketDataProvider / MockMarketDataProvider).
    """
    latest_provider_used: str = "Not recorded"

    @classmethod
    async def get_mandi_prices(
        cls,
        commodity: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
        market_name: Optional[str] = None
    ) -> MarketComparisonResponse:
        # Resolve target district and state gracefully
        target_district = district or (state if state and state not in ("Andhra Pradesh", "Telangana", "Punjab", "Haryana", "Maharashtra") else "Warangal")
        target_state = state if (state and state in ("Andhra Pradesh", "Telangana", "Punjab", "Haryana", "Maharashtra")) else ("Telangana" if target_district in ("Warangal", "Khammam", "Karimnagar", "Hyderabad", "Nizamabad") else "Andhra Pradesh")
        
        provider = MarketProviderFactory.get_provider()
        res = await provider.fetch_prices(
            commodity=commodity,
            state=target_state,
            district=target_district,
            market_name=market_name
        )
        cls.latest_provider_used = res.source or type(provider).__name__
        return res


    @classmethod
    def get_provider_status(cls) -> dict:
        from app.core.config import settings
        primary = (settings.MARKET_PROVIDER or "data_gov").lower()
        fallback = "mock"
        configured = bool(settings.DATA_GOV_API_KEY and not settings.DATA_GOV_API_KEY.startswith("your_"))
        live_status = "ACTIVE" if (configured or primary == "mock") else "DEGRADED"
        return {
            "primary_market_provider": primary,
            "fallback_market_provider": fallback,
            "market_live_status": live_status,
            "market_latest_provider_used": cls.latest_provider_used,
            "market_configured": configured
        }

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
    @staticmethod
    async def get_mandi_prices(
        commodity: str = "Chilli",
        state: str = "Andhra Pradesh",
        district: str = "Guntur",
        market_name: Optional[str] = None
    ) -> MarketComparisonResponse:
        provider = MarketProviderFactory.get_provider()
        return await provider.fetch_prices(
            commodity=commodity,
            state=state,
            district=district,
            market_name=market_name
        )

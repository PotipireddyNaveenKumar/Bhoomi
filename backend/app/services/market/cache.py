import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone, timedelta
from app.schemas.market import MarketComparisonResponse, MarketFreshnessStatus

logger = logging.getLogger(__name__)

class MarketCache:
    """
    Thread-safe in-memory cache for agricultural mandi market quotes.
    Enforces Agmarknet daily freshness lifecycle:
      - CURRENT: Retrieved < 6 hours ago and arrival_date within active trading window
      - CACHED: Retrieved 6 to 24 hours ago
      - STALE: Retrieved >= 24 hours ago or historical record
      - HISTORICAL: Explicit historical snapshot records (never marked CURRENT)
    """
    def __init__(
        self,
        live_window_hours: float = 6.0,
        stale_threshold_hours: float = 24.0
    ):
        self.live_window_hours = live_window_hours
        self.stale_threshold_hours = stale_threshold_hours
        self._cache: Dict[str, Tuple[MarketComparisonResponse, datetime]] = {}

    def make_key(
        self,
        commodity: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
        market: Optional[str] = None,
        target_date: Optional[str] = None
    ) -> str:
        c = commodity.strip().lower()
        s = (state or "all").strip().lower()
        d = (district or "all").strip().lower()
        m = (market or "all").strip().lower()
        dt = (target_date or "latest").strip().lower()
        return f"market:{c}:{s}:{d}:{m}:{dt}"

    def get(self, key: str) -> Optional[Tuple[MarketComparisonResponse, str]]:
        if key not in self._cache:
            return None

        response, cached_at = self._cache[key]
        now = datetime.now(timezone.utc)
        elapsed_hours = (now - cached_at).total_seconds() / 3600.0

        # Preserve explicit HISTORICAL marking
        if response.freshness == MarketFreshnessStatus.HISTORICAL.value:
            return response, MarketFreshnessStatus.HISTORICAL.value

        # Freshness evaluation
        if elapsed_hours < self.live_window_hours:
            status = MarketFreshnessStatus.CURRENT.value
            is_live = True
        elif elapsed_hours < self.stale_threshold_hours:
            status = MarketFreshnessStatus.CACHED.value
            is_live = False
        else:
            status = MarketFreshnessStatus.STALE.value
            is_live = False

        # Clone and return updated freshness attributes
        updated_response = response.model_copy(deep=True)
        updated_response.freshness = status
        updated_response.is_live = is_live
        for opt in updated_response.mandi_options:
            opt.freshness = status
            opt.is_live = is_live

        return updated_response, status

    def set(
        self,
        key: str,
        response: MarketComparisonResponse,
        cached_at: Optional[datetime] = None
    ) -> None:
        ts = cached_at or datetime.now(timezone.utc)
        self._cache[key] = (response, ts)

    def clear(self) -> None:
        self._cache.clear()

# Global singleton market cache instance
market_cache = MarketCache()

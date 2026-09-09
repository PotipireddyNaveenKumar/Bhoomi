from typing import Optional, Dict, Tuple, Any
from datetime import datetime, timezone, timedelta
from app.schemas.weather import WeatherResponse, FreshnessStatus

class WeatherCacheEntry:
    def __init__(self, response: WeatherResponse, cached_at: datetime):
        self.response = response
        self.cached_at = cached_at

class WeatherCache:
    """
    Local in-memory and Redis-backed weather cache with strict freshness validation.
    Prevents redundant external API queries while strictly enforcing provenance.
    """
    CURRENT_WINDOW_SECONDS = 1800      # 30 minutes: CURRENT
    STALE_THRESHOLD_SECONDS = 10800    # 3 hours (180 minutes): STALE beyond this

    def __init__(self):
        self._store: Dict[str, WeatherCacheEntry] = {}

    @staticmethod
    def make_key(location: str, lat: Optional[float] = None, lon: Optional[float] = None) -> str:
        if lat is not None and lon is not None:
            return f"weather:{lat:.2f}:{lon:.2f}"
        return f"weather:{location.lower().strip()}"

    def get(self, key: str) -> Optional[Tuple[WeatherResponse, str]]:
        """
        Retrieves cached weather item with computed freshness.
        Returns (WeatherResponse, FreshnessStatus) or None.
        """
        entry = self._store.get(key)
        if not entry:
            return None

        now = datetime.now(timezone.utc)
        elapsed = (now - entry.cached_at).total_seconds()

        if elapsed < self.CURRENT_WINDOW_SECONDS:
            freshness = FreshnessStatus.CURRENT.value
            is_live = True
        elif elapsed < self.STALE_THRESHOLD_SECONDS:
            freshness = FreshnessStatus.CACHED.value
            is_live = False
        else:
            freshness = FreshnessStatus.STALE.value
            is_live = False

        # Clone and assign freshness
        resp = entry.response.model_copy(deep=True)
        resp.freshness = freshness
        resp.current.freshness = freshness
        resp.current.is_live = is_live

        if freshness == FreshnessStatus.STALE.value:
            time_str = entry.cached_at.strftime("%Y-%m-%d %H:%M UTC")
            resp.current.advisory = (
                f"[STALE ADVISORY - Recorded at {time_str}] "
                f"{resp.current.advisory} (Note: Fresh meteorological update is currently unavailable)."
            )
        elif freshness == FreshnessStatus.CACHED.value:
            time_str = entry.cached_at.strftime("%H:%M UTC")
            resp.current.advisory = (
                f"[CACHED at {time_str}] {resp.current.advisory}"
            )

        return resp, freshness

    def set(self, key: str, response: WeatherResponse, cached_at: Optional[datetime] = None) -> None:
        """Stores normalized weather response in cache."""
        now = cached_at or datetime.now(timezone.utc)
        self._store[key] = WeatherCacheEntry(response=response, cached_at=now)

    def clear(self) -> None:
        """Flushes in-memory cache."""
        self._store.clear()

# Global cache instance
weather_cache = WeatherCache()

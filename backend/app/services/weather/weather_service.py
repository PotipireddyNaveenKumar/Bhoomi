from typing import Optional
from app.schemas.weather import WeatherResponse
from app.services.weather.weather_provider import WeatherProviderFactory

class WeatherService:
    """
    Weather intelligence service facade.
    Dispatches to configured WeatherProvider (Real / OpenWeatherMap / Open-Meteo / Mock).
    Never invents numerical weather facts; returns validated meteorological source data
    with strict data provenance and freshness tracking.
    """
    latest_provider_used: str = "Not recorded"

    @classmethod
    async def get_weather(
        cls,
        location: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        provider_override: Optional[str] = None
    ) -> WeatherResponse:
        target_loc = location or ""
        provider = WeatherProviderFactory.get_provider(provider_override)
        res = await provider.get_current_and_forecast(
            location=target_loc,
            lat=lat,
            lon=lon
        )
        cls.latest_provider_used = res.provider_type or getattr(provider, "provider_type", type(provider).__name__)
        return res

    @classmethod
    def get_provider_status(cls) -> dict:
        from app.core.config import settings
        primary = (settings.WEATHER_PROVIDER or "openweathermap").lower()
        fallback = "openmeteo"
        configured = bool(settings.WEATHER_API_KEY and not settings.WEATHER_API_KEY.startswith("your_"))
        live_status = "ACTIVE" if (configured or primary in ("openmeteo", "mock")) else "DEGRADED"
        return {
            "primary_weather_provider": primary,
            "fallback_weather_provider": fallback,
            "weather_live_status": live_status,
            "weather_latest_provider_used": cls.latest_provider_used,
            "weather_configured": configured
        }

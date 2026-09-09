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
    @staticmethod
    async def get_weather(
        location: str = "Guntur",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        provider_override: Optional[str] = None
    ) -> WeatherResponse:
        provider = WeatherProviderFactory.get_provider(provider_override)
        return await provider.get_current_and_forecast(
            location=location,
            lat=lat,
            lon=lon
        )

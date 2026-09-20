import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from app.schemas.weather import WeatherResponse, WeatherCurrent, WeatherForecastDay, FreshnessStatus
from app.core.config import settings

logger = logging.getLogger(__name__)

class WeatherProvider(ABC):
    @abstractmethod
    async def get_current_and_forecast(
        self,
        location: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> WeatherResponse:
        pass

class MockWeatherProvider(WeatherProvider):
    async def get_current_and_forecast(
        self,
        location: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> WeatherResponse:
        from datetime import timedelta, date
        now_utc = datetime.now(timezone.utc)
        today_date = date.today()
        today_iso = today_date.isoformat()
        tomorrow_iso = (today_date + timedelta(days=1)).isoformat()
        day2_iso = (today_date + timedelta(days=2)).isoformat()
        day3_iso = (today_date + timedelta(days=3)).isoformat()

        current = WeatherCurrent(
            temperature_c=31.5,
            humidity_percent=68.0,
            rainfall_mm=2.4,
            wind_speed_kmh=12.0,
            weather_condition="Partly Cloudy with Scattered Showers",
            rain_probability_percent=40,
            advisory="Light rain expected in late afternoon. You can defer today's surface irrigation.",
            is_live=False,
            timestamp=now_utc,
            retrieved_at=now_utc,
            calendar_date=today_iso,
            timezone="Asia/Kolkata",
            observation_type="CURRENT_OBSERVATION",
            freshness=FreshnessStatus.CURRENT.value,
            source="IMD Agro-Meteorological Advisory (Certified Offline Cache)"
        )

        forecast = [
            WeatherForecastDay(
                date="Tomorrow",
                calendar_date=tomorrow_iso,
                day_name="Tomorrow",
                timezone="Asia/Kolkata",
                observation_type="FORECAST",
                temp_max=33.0,
                temp_min=24.0,
                rain_probability=45,
                condition="Scattered Clouds",
                rainfall_mm=2.0,
                wind_speed_kmh=11.0
            ),
            WeatherForecastDay(
                date=f"Day 2 ({day2_iso})",
                calendar_date=day2_iso,
                day_name=(today_date + timedelta(days=2)).strftime("%A"),
                timezone="Asia/Kolkata",
                observation_type="FORECAST",
                temp_max=34.0,
                temp_min=25.0,
                rain_probability=20,
                condition="Sunny / Clear",
                rainfall_mm=0.0,
                wind_speed_kmh=9.0
            ),
            WeatherForecastDay(
                date=f"Day 3 ({day3_iso})",
                calendar_date=day3_iso,
                day_name=(today_date + timedelta(days=3)).strftime("%A"),
                timezone="Asia/Kolkata",
                observation_type="FORECAST",
                temp_max=35.0,
                temp_min=25.0,
                rain_probability=10,
                condition="Clear Sky",
                rainfall_mm=0.0,
                wind_speed_kmh=8.0
            ),
        ]

        from app.services.weather.real_provider import RealWeatherProvider
        spray_eval = RealWeatherProvider.evaluate_spray_window(
            rain_prob=forecast[0].rain_probability,
            rainfall_mm=forecast[0].rainfall_mm,
            wind_speed_kmh=forecast[0].wind_speed_kmh,
            temp_c=forecast[0].temp_max,
            target_date=tomorrow_iso,
            data_freshness=FreshnessStatus.CURRENT.value
        )
        irr_eval = RealWeatherProvider.evaluate_irrigation(
            today_rain_prob=current.rain_probability_percent,
            today_rainfall_mm=current.rainfall_mm,
            tomorrow_rain_prob=forecast[0].rain_probability,
            tomorrow_rainfall_mm=forecast[0].rainfall_mm
        )

        return WeatherResponse(
            location=location,
            latitude=lat or 16.3067,
            longitude=lon or 80.4365,
            current=current,
            forecast_3_days=forecast,
            source="Demo / Synthetic Weather Advisory (Offline Demonstration)",
            target_date=tomorrow_iso,
            target_date_range=f"{today_iso} to {day3_iso}",
            timezone="Asia/Kolkata",
            provider_type="MOCK",
            freshness=FreshnessStatus.DEMO.value,
            retrieved_at=now_utc.isoformat(),
            provider_status="DEMO",
            requires_api_key=False,
            configured=True,
            spray_window_evaluation=spray_eval,
            irrigation_evaluation=irr_eval
        )

class WeatherProviderFactory:
    _instance: Optional[WeatherProvider] = None

    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> WeatherProvider:
        # Import inside method to prevent circular dependencies
        from app.services.weather.real_provider import RealWeatherProvider

        name = (provider_name or os.environ.get("WEATHER_PROVIDER") or settings.WEATHER_PROVIDER or "mock").lower().strip()
        api_key = os.environ.get("WEATHER_API_KEY") or settings.WEATHER_API_KEY

        if name == "mock":
            if settings.APP_ENV in ["production", "staging"]:
                logger.warning("MockWeatherProvider forbidden in %s; activating Open-Meteo real provider.", settings.APP_ENV)
                return RealWeatherProvider(api_key=None, provider_type="openmeteo")
            return MockWeatherProvider()

        if name in ("real", "openweathermap"):
            if api_key and not api_key.startswith("your_"):
                return RealWeatherProvider(api_key=api_key, provider_type="openweathermap")
            # If real requested but no OWM key, use Open-Meteo as high-precision open alternative
            logger.info("WEATHER_API_KEY not configured or placeholder; activating Open-Meteo real provider.")
            return RealWeatherProvider(api_key=None, provider_type="openmeteo")

        if name == "openmeteo":
            return RealWeatherProvider(api_key=None, provider_type="openmeteo")

        logger.warning("Unrecognized weather provider '%s'; defaulting to MockWeatherProvider.", name)
        return MockWeatherProvider()

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

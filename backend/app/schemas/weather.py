from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

class FreshnessStatus(str, Enum):
    CURRENT = "CURRENT"
    CACHED = "CACHED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    DEMO = "DEMO"
    SYNTHETIC = "SYNTHETIC"

class WeatherCurrent(BaseModel):
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    rainfall_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    weather_condition: str = "Clear"
    rain_probability_percent: Optional[int] = None
    advisory: str
    is_live: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    observed_at: Optional[datetime] = None
    retrieved_at: Optional[datetime] = None
    calendar_date: Optional[str] = None
    timezone: str = "Asia/Kolkata"
    observation_type: str = "CURRENT_OBSERVATION"
    freshness: str = FreshnessStatus.CURRENT.value
    source: Optional[str] = None

class WeatherForecastDay(BaseModel):
    date: str
    calendar_date: Optional[str] = None
    day_name: Optional[str] = None
    timezone: str = "Asia/Kolkata"
    observation_type: str = "FORECAST"
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None
    rain_probability: Optional[int] = None
    condition: str = "Clear"
    rainfall_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None

class WeatherResponse(BaseModel):
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current: WeatherCurrent
    forecast_3_days: List[WeatherForecastDay]
    source: str
    target_date: Optional[str] = None
    target_date_range: Optional[str] = None
    timezone: str = "Asia/Kolkata"
    provider_type: Optional[str] = None
    freshness: str = FreshnessStatus.CURRENT.value
    retrieved_at: Optional[str] = None
    provider_status: Optional[str] = None
    requires_api_key: bool = False
    configured: bool = True
    spray_window_evaluation: Optional[Dict[str, Any]] = None
    irrigation_evaluation: Optional[Dict[str, Any]] = None

    @property
    def forecast(self) -> List[WeatherForecastDay]:
        return self.forecast_3_days


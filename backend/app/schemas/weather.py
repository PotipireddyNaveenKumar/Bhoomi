from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

class FreshnessStatus(str, Enum):
    CURRENT = "CURRENT"
    CACHED = "CACHED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"

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
    freshness: str = FreshnessStatus.CURRENT.value
    source: Optional[str] = None

class WeatherForecastDay(BaseModel):
    date: str
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None
    rain_probability: Optional[int] = None
    condition: str = "Clear"
    rainfall_mm: Optional[float] = None

class WeatherResponse(BaseModel):
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current: WeatherCurrent
    forecast_3_days: List[WeatherForecastDay]
    source: str
    freshness: str = FreshnessStatus.CURRENT.value
    retrieved_at: Optional[str] = None

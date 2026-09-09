from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.services.weather.weather_service import WeatherService
from app.services.farm_manager.weather_decision import WeatherDecisionEngine, WeatherDecisionResult
from app.schemas.weather import WeatherResponse

router = APIRouter(prefix="/weather", tags=["Weather Intelligence"])

@router.get("", response_model=WeatherResponse)
async def get_weather(
    location: Optional[str] = Query(default=None),
    lat: Optional[float] = Query(default=None),
    lon: Optional[float] = Query(default=None),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
):
    loc = location or getattr(farmer, "district", None) or "Guntur"
    return await WeatherService.get_weather(location=loc, lat=lat, lon=lon)

@router.get("/forecast")
async def get_weather_forecast(
    location: Optional[str] = Query(default=None),
    lat: Optional[float] = Query(default=None),
    lon: Optional[float] = Query(default=None),
    crop_stage: str = Query(default="flowering"),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
):
    loc = location or getattr(farmer, "district", None) or "Guntur"
    weather_res = await WeatherService.get_weather(location=loc, lat=lat, lon=lon)
    decision = WeatherDecisionEngine.evaluate(
        weather_data=weather_res.current.model_dump(),
        soil_type="black",
        crop_stage=crop_stage
    )
    return {
        "weather": weather_res,
        "agronomic_decision": decision
    }

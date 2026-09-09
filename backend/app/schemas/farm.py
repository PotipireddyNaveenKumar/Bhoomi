from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field

class CropCreate(BaseModel):
    crop_name: str = Field(..., example="Chilli")
    variety: Optional[str] = Field(default=None, example="Teja")
    area_acres: Decimal = Field(..., example=3.0)
    sowing_date: Optional[date] = None
    expected_harvest_date: Optional[date] = None
    current_stage: str = Field(default="vegetative", example="vegetative")
    cultivation_cost_spent: Optional[Decimal] = Field(default=Decimal("0.0"))

class CropResponse(CropCreate):
    id: str
    farm_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FarmCreate(BaseModel):
    farm_name: str = Field(default="My Main Farm", example="My Main Farm")
    total_area_acres: Decimal = Field(..., example=3.0)
    latitude: Optional[float] = Field(default=16.3067)
    longitude: Optional[float] = Field(default=80.4365)
    soil_type: Optional[str] = Field(default="black", example="black")
    irrigation_source: Optional[str] = Field(default="borewell", example="borewell")
    soil_health_data: Optional[Dict[str, Any]] = None

class FarmUpdate(BaseModel):
    farm_name: Optional[str] = None
    total_area_acres: Optional[Decimal] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    soil_type: Optional[str] = None
    irrigation_source: Optional[str] = None
    soil_health_data: Optional[Dict[str, Any]] = None

class FarmResponse(FarmCreate):
    id: str
    farmer_id: str
    crops: List[CropResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

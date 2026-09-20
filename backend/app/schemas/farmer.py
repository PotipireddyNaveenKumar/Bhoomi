from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.farm import FarmResponse

class FarmerProfileBase(BaseModel):
    name: str
    preferred_language: str = "en"
    state: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    experience_years: Optional[int] = 0

class FarmerProfileUpdate(BaseModel):
    name: Optional[str] = None
    preferred_language: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    experience_years: Optional[int] = None

class FarmerProfileResponse(FarmerProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FarmerOnboardRequest(BaseModel):
    name: str = Field(..., example="Ramesh Rao", description="Farmer full name")
    preferred_language: Optional[str] = Field(default="en", example="te")
    state: Optional[str] = Field(default=None, example="Andhra Pradesh")
    district: Optional[str] = Field(default=None, example="Guntur")
    village: Optional[str] = Field(default=None, example="Tenali")
    current_crop: str = Field(..., example="Chilli", description="Primary cultivated crop")
    crop_variety: Optional[str] = Field(default=None, example="Teja")
    land_area_acres: float = Field(..., gt=0, example=3.0, description="Total land area in acres")
    soil_type: Optional[str] = Field(default="black", example="black")
    soil_source_type: Optional[str] = Field(default="estimated", example="estimated")
    soil_n: Optional[float] = Field(default=None, example=120.0)
    soil_p: Optional[float] = Field(default=None, example=40.0)
    soil_k: Optional[float] = Field(default=None, example=60.0)
    soil_ph: Optional[float] = Field(default=6.5, example=6.8)
    latitude: Optional[float] = Field(default=None, example=16.3067)
    longitude: Optional[float] = Field(default=None, example=80.4365)
    irrigation_source: Optional[str] = Field(default="borewell", example="borewell")


class FarmerOnboardResponse(BaseModel):
    success: bool = True
    message: str = "Onboarding completed successfully"
    farmer: FarmerProfileResponse
    farm: Optional[FarmResponse] = None

    class Config:
        from_attributes = True


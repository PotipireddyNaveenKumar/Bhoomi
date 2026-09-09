from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

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

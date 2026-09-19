from typing import Optional
from pydantic import BaseModel, Field

class UserRegisterRequest(BaseModel):
    phone_number: str = Field(..., example="+919876543210")
    password: str = Field(..., min_length=6)
    name: str = Field(..., example="Ramesh Kumar")
    preferred_language: str = Field(default="te", example="te")  # en, te, hi, ta, kn, ml
    state: Optional[str] = Field(default=None)
    district: Optional[str] = Field(default=None)
    village: Optional[str] = Field(default=None)

class UserLoginRequest(BaseModel):
    phone_number: str = Field(..., example="+919876543210")
    password: str = Field(...)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    farmer_id: str
    name: str
    preferred_language: str
    state: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    farm_id: Optional[str] = None
    crop_name: Optional[str] = None
    area_acres: Optional[float] = None
    soil_type: Optional[str] = None
    is_new_user: bool = False

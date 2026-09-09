from typing import Optional
from pydantic import BaseModel, Field

class UserRegisterRequest(BaseModel):
    phone_number: str = Field(..., example="+919876543210")
    password: str = Field(..., min_length=6)
    name: str = Field(..., example="Ramesh Kumar")
    preferred_language: str = Field(default="te", example="te")  # en, te, hi, ta, kn, ml
    state: Optional[str] = Field(default="Andhra Pradesh")
    district: Optional[str] = Field(default="Guntur")
    village: Optional[str] = Field(default="Tenali")

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

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class UserRegisterRequest(BaseModel):
    phone_number: str = Field(..., json_schema_extra={"example": "+919876543210"})
    password: str = Field(..., min_length=6)
    name: str = Field(..., json_schema_extra={"example": "Ramesh Kumar"})
    preferred_language: str = Field(default="te", json_schema_extra={"example": "te"})
    state: Optional[str] = Field(default=None)
    district: Optional[str] = Field(default=None)
    village: Optional[str] = Field(default=None)

class UserLoginRequest(BaseModel):
    phone_number: Optional[str] = Field(default=None, json_schema_extra={"example": "+919876543210"})
    password: Optional[str] = Field(default=None)
    is_demo: Optional[bool] = Field(default=False)

    @model_validator(mode="after")
    def validate_credentials_or_demo(self):
        if not self.is_demo:
            if not self.phone_number or not self.password:
                raise ValueError("Both phone_number and password are required unless is_demo is True.")
        return self

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
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

# --- Canonical BHOOMI OTP & Session Schemas ---

class PhoneOtpRequest(BaseModel):
    phone_number: str = Field(..., json_schema_extra={"example": "+919876543210"})

class VerifyOtpOnlyRequest(BaseModel):
    phone_number: str = Field(..., json_schema_extra={"example": "+919876543210"})
    otp: str = Field(..., min_length=6, max_length=6, json_schema_extra={"example": "583214"})

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(...)

class OtpResponse(BaseModel):
    success: bool = True
    message: str
    delivery_channel: str = "sms"
    expires_in: int = 600
    resend_after: int = 30

class UserSummary(BaseModel):
    id: str
    phone_number: str
    phone_number_verified: bool

class AuthSuccessResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserSummary
    onboarding_required: bool

class FarmerProfileBrief(BaseModel):
    id: str
    name: str
    preferred_language: str
    state: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None

class FarmBrief(BaseModel):
    id: str
    farm_name: str
    total_area_acres: float
    soil_type: Optional[str] = None
    crop_name: Optional[str] = None

class CurrentUserResponse(BaseModel):
    id: str
    phone_number: str
    phone_number_verified: bool
    is_active: bool
    farmer_profile: Optional[FarmerProfileBrief] = None
    farm: Optional[FarmBrief] = None
    onboarding_required: bool

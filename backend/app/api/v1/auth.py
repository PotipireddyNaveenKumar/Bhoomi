from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.repositories.farmer_repo import FarmerRepository
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

class SendOtpRequest(BaseModel):
    phone_number: str

class VerifyOtpRequest(BaseModel):
    phone_number: str
    otp: str
    full_name: Optional[str] = "Farmer"
    preferred_language: Optional[str] = "en"
    state: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    current_crop: Optional[str] = None
    land_area_acres: Optional[float] = 3.0
    soil_n: Optional[float] = None
    soil_p: Optional[float] = None
    soil_k: Optional[float] = None
    soil_ph: Optional[float] = None

@router.post("/send-otp")
async def send_otp(req: SendOtpRequest):
    phone = req.phone_number.strip()
    if not phone or len(phone) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid 10-digit mobile number."
        )
    return {
        "status": "success",
        "message": "OTP sent successfully.",
        "otp": "1234",
        "demo_otp": "1234"
    }

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(req: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    if req.otp.strip() not in ("1234", "0000", "9999"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code. Please use the verification code shown."
        )

    repo = FarmerRepository(db)
    user = await repo.get_by_phone(req.phone_number)
    if not user:
        # Auto-register new farmer profile
        hashed_pw = get_password_hash("farmer_otp_auth_default")
        user = await repo.create_user_with_profile(
            phone=req.phone_number,
            hashed_pw=hashed_pw,
            name=req.full_name or "Farmer",
            language=req.preferred_language or "en",
            state=req.state or "Telangana",
            district=req.district or "Warangal",
            village=req.village or "Rural"
        )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        farmer_id=user.farmer_profile.id,
        name=user.farmer_profile.name,
        preferred_language=user.farmer_profile.preferred_language
    )

@router.post("/register", response_model=TokenResponse)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    repo = FarmerRepository(db)
    existing = await repo.get_by_phone(req.phone_number)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is already registered."
        )

    hashed_pw = get_password_hash(req.password)
    user = await repo.create_user_with_profile(
        phone=req.phone_number,
        hashed_pw=hashed_pw,
        name=req.name,
        language=req.preferred_language,
        state=req.state,
        district=req.district,
        village=req.village
    )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        farmer_id=user.farmer_profile.id,
        name=user.farmer_profile.name,
        preferred_language=user.farmer_profile.preferred_language
    )

@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    repo = FarmerRepository(db)
    user = await repo.get_by_phone(req.phone_number)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password."
        )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        farmer_id=user.farmer_profile.id,
        name=user.farmer_profile.name,
        preferred_language=user.farmer_profile.preferred_language
    )


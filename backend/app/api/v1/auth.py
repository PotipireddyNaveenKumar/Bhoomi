from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.repositories.farmer_repo import FarmerRepository
from app.repositories.farm_repo import FarmRepository
from app.schemas.farm import FarmCreate, CropCreate
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse
from app.services.soil.soil_estimation_service import SoilEstimationService

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
    crop_variety: Optional[str] = None
    land_area_acres: Optional[float] = 3.0
    soil_type: Optional[str] = None
    soil_n: Optional[float] = None
    soil_p: Optional[float] = None
    soil_k: Optional[float] = None
    soil_ph: Optional[float] = None
    soil_source_type: Optional[str] = "estimated"
    soil_data: Optional[Dict[str, Any]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

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
        "message": "OTP sent successfully. Enter 1234 to verify.",
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

    phone_clean = req.phone_number.strip()
    repo = FarmerRepository(db)
    farm_repo = FarmRepository(db)
    user = await repo.get_by_phone(phone_clean)
    
    state_val = req.state or "Telangana"
    district_val = req.district or "Warangal"
    village_val = req.village or "Rural"
    name_val = req.full_name or "Farmer"
    lang_val = req.preferred_language or "en"

    # Obtain location soil estimation if soil_type not provided
    soil_est = SoilEstimationService.get_soil_estimate(
        state=state_val,
        district=district_val,
        latitude=req.latitude,
        longitude=req.longitude
    )
    resolved_soil_type = req.soil_type or soil_est.soil_type

    # Construct structured soil health data with explicit provenance
    source_type = req.soil_source_type or ("farmer_entered" if (req.soil_n or req.soil_p or req.soil_k) else "estimated")
    soil_health = {
        "pH": {
            "value": req.soil_ph if req.soil_ph is not None else soil_est.estimated_ph,
            "source_type": "farmer_entered" if req.soil_ph is not None else "estimated",
            "source": "Farmer Soil Health Card" if req.soil_ph is not None else soil_est.source,
            "confidence": 1.0 if req.soil_ph is not None else soil_est.confidence
        },
        "soil_type": {
            "value": resolved_soil_type,
            "source_type": "farmer_entered" if req.soil_type else "estimated",
            "source": "Farmer Selected" if req.soil_type else soil_est.source
        },
        "nitrogen": {
            "value": req.soil_n,
            "display_value": f"{req.soil_n} kg/ha" if req.soil_n is not None else "Not Available from Location",
            "source_type": "farmer_entered" if req.soil_n is not None else "not_available_from_location",
            "source": "Soil Health Card" if req.soil_n is not None else "Laboratory measurement required",
            "confidence": 1.0 if req.soil_n is not None else 0.0
        },
        "phosphorus": {
            "value": req.soil_p,
            "display_value": f"{req.soil_p} kg/ha" if req.soil_p is not None else "Not Available from Location",
            "source_type": "farmer_entered" if req.soil_p is not None else "not_available_from_location",
            "source": "Soil Health Card" if req.soil_p is not None else "Laboratory measurement required",
            "confidence": 1.0 if req.soil_p is not None else 0.0
        },
        "potassium": {
            "value": req.soil_k,
            "display_value": f"{req.soil_k} kg/ha" if req.soil_k is not None else "Not Available from Location",
            "source_type": "farmer_entered" if req.soil_k is not None else "not_available_from_location",
            "source": "Soil Health Card" if req.soil_k is not None else "Laboratory measurement required",
            "confidence": 1.0 if req.soil_k is not None else 0.0
        },
        "location_metadata": {
            "state": state_val,
            "district": district_val,
            "village": village_val,
            "latitude": req.latitude,
            "longitude": req.longitude
        }
    }
    if req.soil_data:
        soil_health.update(req.soil_data)

    if not user:
        # Auto-register new farmer profile
        hashed_pw = get_password_hash("farmer_otp_auth_default")
        user = await repo.create_user_with_profile(
            phone=phone_clean,
            hashed_pw=hashed_pw,
            name=name_val,
            language=lang_val,
            state=state_val,
            district=district_val,
            village=village_val
        )
    elif not user.farmer_profile:
        from app.models.farmer import FarmerProfile
        profile = FarmerProfile(
            user_id=user.id,
            name=name_val,
            preferred_language=lang_val,
            state=state_val,
            district=district_val,
            village=village_val
        )
        db.add(profile)
        await db.commit()
        user.farmer_profile = profile
    else:
        # Update existing profile with newly entered location details
        if req.full_name:
            user.farmer_profile.name = name_val
        if req.preferred_language:
            user.farmer_profile.preferred_language = lang_val
        if req.state:
            user.farmer_profile.state = state_val
        if req.district:
            user.farmer_profile.district = district_val
        if req.village:
            user.farmer_profile.village = village_val
        await db.commit()

    # Ensure farmer has a Farm and FarmCrop in the Digital Twin
    farmer_id = user.farmer_profile.id
    existing_farms = await farm_repo.get_farms_by_farmer(farmer_id)
    farm = None
    if not existing_farms:
        farm_create = FarmCreate(
            farm_name=f"{name_val}'s Farm",
            total_area_acres=Decimal(str(req.land_area_acres or 3.0)),
            latitude=req.latitude or (17.9689 if state_val == "Telangana" else 16.3067),
            longitude=req.longitude or (79.5941 if state_val == "Telangana" else 80.4365),
            soil_type=resolved_soil_type,
            irrigation_source="borewell",
            soil_health_data=soil_health
        )
        farm = await farm_repo.create_farm(farmer_id, farm_create)
    else:
        farm = existing_farms[0]
        # Update farm attributes if newly provided
        farm.total_area_acres = Decimal(str(req.land_area_acres or farm.total_area_acres))
        farm.soil_type = resolved_soil_type
        farm.soil_health_data = soil_health
        if req.latitude:
            farm.latitude = req.latitude
        if req.longitude:
            farm.longitude = req.longitude
        await db.commit()
        await db.refresh(farm)

    # Ensure the active crop is registered on this farm
    crop_name = req.current_crop or "Chilli"
    if farm:
        if not farm.crops or len(farm.crops) == 0:
            crop_in = CropCreate(
                crop_name=crop_name,
                variety=req.crop_variety,
                area_acres=Decimal(str(req.land_area_acres or 3.0)),
                current_stage="vegetative"
            )
            await farm_repo.add_crop_to_farm(farm.id, crop_in)
        else:
            # If user explicitly selected a crop during onboarding, update existing primary crop
            if req.current_crop:
                primary_crop = farm.crops[0]
                primary_crop.crop_name = req.current_crop
                if req.crop_variety:
                    primary_crop.variety = req.crop_variety
                if req.land_area_acres:
                    primary_crop.area_acres = Decimal(str(req.land_area_acres))
                await db.commit()

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        farmer_id=farmer_id,
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


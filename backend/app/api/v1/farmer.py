from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.schemas.farmer import (
    FarmerProfileResponse,
    FarmerProfileUpdate,
    FarmerOnboardRequest,
    FarmerOnboardResponse
)


router = APIRouter(prefix="/farmer", tags=["Farmer Profile"])

@router.get("", response_model=FarmerProfileResponse)
async def get_profile(farmer: FarmerProfile = Depends(get_current_farmer_profile)):
    return farmer

@router.put("", response_model=FarmerProfileResponse)
async def update_profile(
    update_in: FarmerProfileUpdate,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    if update_in.name is not None:
        farmer.name = update_in.name
    if update_in.preferred_language is not None:
        farmer.preferred_language = update_in.preferred_language
    if update_in.state is not None:
        farmer.state = update_in.state
    if update_in.district is not None:
        farmer.district = update_in.district
    if update_in.village is not None:
        farmer.village = update_in.village
    if update_in.experience_years is not None:
        farmer.experience_years = update_in.experience_years

    await db.commit()
    await db.refresh(farmer)
    return farmer


@router.post("/onboard", response_model=FarmerOnboardResponse)
async def onboard_farmer(
    req: FarmerOnboardRequest,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Canonical End-to-End Farmer Onboarding Endpoint.
    Atomically updates FarmerProfile, provisions the Farm, and records the initial FarmCrop.
    Guarantees atomic rollback on failure and eager-loads relationships to prevent lazy loading errors.
    """
    from decimal import Decimal
    from app.repositories.farm_repo import FarmRepository
    from app.schemas.farm import FarmResponse

    try:
        # 1. Update Farmer Profile
        farmer.name = req.name.strip()
        if req.preferred_language:
            farmer.preferred_language = req.preferred_language
        farmer.state = req.state
        farmer.district = req.district
        farmer.village = req.village

        # 2. Prepare soil health JSON data
        soil_health_data = {}
        if req.soil_source_type:
            soil_health_data["source"] = req.soil_source_type
        if req.soil_n is not None:
            soil_health_data["N"] = req.soil_n
        if req.soil_p is not None:
            soil_health_data["P"] = req.soil_p
        if req.soil_k is not None:
            soil_health_data["K"] = req.soil_k
        if req.soil_ph is not None:
            soil_health_data["pH"] = req.soil_ph

        # 3. Atomically provision Farm and Initial FarmCrop
        farm_repo = FarmRepository(db)
        farm = await farm_repo.atomic_onboard_farm_and_crop(
            farmer_id=farmer.id,
            farm_name=f"{req.name}'s Farm",
            total_area_acres=Decimal(str(req.land_area_acres)),
            soil_type=req.soil_type or "black",
            irrigation_source=req.irrigation_source or "borewell",
            soil_health_data=soil_health_data or None,
            latitude=req.latitude,
            longitude=req.longitude,
            crop_name=req.current_crop,
            crop_variety=req.crop_variety
        )

        # 4. Refresh farmer profile
        await db.refresh(farmer)

        # 5. Serialize farm safely
        farm_dto = FarmResponse.model_validate(farm)

        return FarmerOnboardResponse(
            success=True,
            message="Onboarding completed successfully",
            farmer=FarmerProfileResponse.model_validate(farmer),
            farm=farm_dto
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Onboarding failed: {str(e)}"
        )


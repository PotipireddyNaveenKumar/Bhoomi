from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.schemas.farmer import FarmerProfileResponse, FarmerProfileUpdate

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

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.repositories.farm_repo import FarmRepository
from app.schemas.farm import FarmCreate, FarmResponse, CropCreate, CropResponse

router = APIRouter(prefix="/farms", tags=["Farm Digital Twin"])

@router.get("", response_model=List[FarmResponse])
async def list_farms(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = FarmRepository(db)
    return await repo.get_farms_by_farmer(farmer.id)

@router.post("", response_model=FarmResponse)
async def create_farm(
    farm_in: FarmCreate,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = FarmRepository(db)
    return await repo.create_farm(farmer.id, farm_in)

@router.get("/{farm_id}", response_model=FarmResponse)
async def get_farm(
    farm_id: str,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = FarmRepository(db)
    farm = await repo.get_farm_by_id(farm_id, farmer.id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found.")
    return farm

@router.post("/{farm_id}/crops", response_model=CropResponse)
async def add_crop_to_farm(
    farm_id: str,
    crop_in: CropCreate,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = FarmRepository(db)
    farm = await repo.get_farm_by_id(farm_id, farmer.id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found.")
    return await repo.add_crop_to_farm(farm_id, crop_in)

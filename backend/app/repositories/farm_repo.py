from typing import Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.farm import Farm
from app.models.crop import FarmCrop
from app.schemas.farm import FarmCreate, FarmUpdate, CropCreate

class FarmRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_farms_by_farmer(self, farmer_id: str) -> List[Farm]:
        result = await self.db.execute(
            select(Farm).options(selectinload(Farm.crops)).where(Farm.farmer_id == farmer_id)
        )
        return list(result.scalars().all())

    async def get_farm_by_id(self, farm_id: str, farmer_id: str) -> Optional[Farm]:
        result = await self.db.execute(
            select(Farm).options(selectinload(Farm.crops)).where(Farm.id == farm_id, Farm.farmer_id == farmer_id)
        )
        return result.scalars().first()

    async def create_farm(self, farmer_id: str, farm_in: FarmCreate) -> Farm:
        farm = Farm(
            farmer_id=farmer_id,
            farm_name=farm_in.farm_name,
            total_area_acres=farm_in.total_area_acres,
            latitude=farm_in.latitude,
            longitude=farm_in.longitude,
            soil_type=farm_in.soil_type,
            irrigation_source=farm_in.irrigation_source,
            soil_health_data=farm_in.soil_health_data,
        )
        self.db.add(farm)
        await self.db.commit()
        # Eager load crops to eliminate SQLAlchemy MissingGreenlet lazy-loading error on FarmResponse serialization
        res = await self.db.execute(
            select(Farm).options(selectinload(Farm.crops)).where(Farm.id == farm.id)
        )
        return res.scalars().first()

    async def atomic_onboard_farm_and_crop(
        self,
        farmer_id: str,
        farm_name: str,
        total_area_acres: Decimal,
        soil_type: Optional[str],
        irrigation_source: Optional[str],
        soil_health_data: Optional[dict],
        latitude: Optional[float],
        longitude: Optional[float],
        crop_name: str,
        crop_variety: Optional[str] = None
    ) -> Farm:
        farm = Farm(
            farmer_id=farmer_id,
            farm_name=farm_name,
            total_area_acres=total_area_acres,
            latitude=latitude,
            longitude=longitude,
            soil_type=soil_type or "black",
            irrigation_source=irrigation_source or "borewell",
            soil_health_data=soil_health_data,
        )
        self.db.add(farm)
        await self.db.flush()

        crop = FarmCrop(
            farm_id=farm.id,
            crop_name=crop_name,
            variety=crop_variety,
            area_acres=total_area_acres,
            current_stage="vegetative",
            status="active",
            cultivation_cost_spent=Decimal("0.0"),
        )
        self.db.add(crop)
        await self.db.commit()

        # Eager load crops so serializer receives pre-loaded relationship
        res = await self.db.execute(
            select(Farm).options(selectinload(Farm.crops)).where(Farm.id == farm.id)
        )
        return res.scalars().first()


    async def add_crop_to_farm(self, farm_id: str, crop_in: CropCreate) -> FarmCrop:
        crop = FarmCrop(
            farm_id=farm_id,
            crop_name=crop_in.crop_name,
            variety=crop_in.variety,
            area_acres=crop_in.area_acres,
            sowing_date=crop_in.sowing_date,
            expected_harvest_date=crop_in.expected_harvest_date,
            current_stage=crop_in.current_stage,
            cultivation_cost_spent=crop_in.cultivation_cost_spent or Decimal("0.0"),
        )
        self.db.add(crop)
        await self.db.commit()
        await self.db.refresh(crop)
        return crop

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.models.farm import Farm
from app.models.crop import FarmCrop

class FarmerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).options(selectinload(User.farmer_profile)).where(User.phone_number == phone)
        )
        return result.scalars().first()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).options(selectinload(User.farmer_profile)).where(User.id == user_id)
        )
        return result.scalars().first()

    async def get_profile_by_user_id(self, user_id: str) -> Optional[FarmerProfile]:
        result = await self.db.execute(
            select(FarmerProfile).where(FarmerProfile.user_id == user_id)
        )
        return result.scalars().first()

    async def get_profile_by_id(self, farmer_id: str) -> Optional[FarmerProfile]:
        result = await self.db.execute(
            select(FarmerProfile).options(
                selectinload(FarmerProfile.farms).selectinload(Farm.crops),
                selectinload(FarmerProfile.memories),
            ).where(FarmerProfile.id == farmer_id)
        )
        return result.scalars().first()

    async def create_user_with_profile(
        self, phone: str, hashed_pw: str, name: str, language: str = "en",
        state: Optional[str] = None, district: Optional[str] = None, village: Optional[str] = None
    ) -> User:
        user = User(phone_number=phone, hashed_password=hashed_pw)
        self.db.add(user)
        await self.db.flush()

        profile = FarmerProfile(
            user_id=user.id,
            name=name,
            preferred_language=language,
            state=state,
            district=district,
            village=village
        )
        self.db.add(profile)
        await self.db.commit()
        user.farmer_profile = profile
        return user

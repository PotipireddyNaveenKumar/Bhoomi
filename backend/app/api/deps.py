from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_db
from app.repositories.farmer_repo import FarmerRepository
from app.models.user import User
from app.models.farmer import FarmerProfile

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    if not token:
        return None
    if token == "demo_session_token_bhoomi_v2":
        if settings.effective_env in ["production", "staging"] and not settings.DEMO_MODE:
            return None
        farmer_repo = FarmerRepository(db)
        return await farmer_repo.get_by_id("demo_user_1")
    if token.startswith("demo_"):
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    farmer_repo = FarmerRepository(db)
    user = await farmer_repo.get_by_id(user_id)
    return user

def get_canonical_demo_farmer_profile() -> FarmerProfile:
    return FarmerProfile(
        id="demo_farmer_1",
        user_id="demo_user_1",
        name="Ramesh Kumar (Demo Farmer)",
        preferred_language="te",
        state="Andhra Pradesh",
        district="Guntur",
        village="Tenali",
        experience_years=15
    )

async def get_current_farmer_profile(
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FarmerProfile:
    if user and user.farmer_profile:
        return user.farmer_profile

    if settings.DEMO_MODE:
        farmer_repo = FarmerRepository(db)
        demo_user = await farmer_repo.get_by_id("demo_user_1")
        if demo_user and demo_user.farmer_profile:
            return demo_user.farmer_profile
        from app.services.demo.demo_service import DemoModeService
        await DemoModeService.ensure_canonical_demo_data(db)
        demo_user = await farmer_repo.get_by_id("demo_user_1")
        if demo_user and demo_user.farmer_profile:
            return demo_user.farmer_profile
        return get_canonical_demo_farmer_profile()

    if settings.APP_ENV in ["production", "staging"] or settings.effective_env in ["production", "staging"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in to access your farm digital twin.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In development/test mode only, fallback to seeded demo profile for quick developer testing
    farmer_repo = FarmerRepository(db)
    demo_user = await farmer_repo.get_by_id("demo_user_1")
    if demo_user and demo_user.farmer_profile:
        return demo_user.farmer_profile

    return get_canonical_demo_farmer_profile()

async def get_current_farmer_profile_optional(
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[FarmerProfile]:
    if user and user.farmer_profile:
        return user.farmer_profile

    if settings.DEMO_MODE or (settings.APP_ENV not in ["production", "staging"] and settings.effective_env not in ["production", "staging"]):
        farmer_repo = FarmerRepository(db)
        demo_user = await farmer_repo.get_by_id("demo_user_1")
        if demo_user and demo_user.farmer_profile:
            return demo_user.farmer_profile
        from app.services.demo.demo_service import DemoModeService
        await DemoModeService.ensure_canonical_demo_data(db)
        demo_user = await farmer_repo.get_by_id("demo_user_1")
        if demo_user and demo_user.farmer_profile:
            return demo_user.farmer_profile
        return get_canonical_demo_farmer_profile()

    return None

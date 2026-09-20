from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User
from app.services.demo.demo_service import DemoModeService


async def verify_demo_access(user: Optional[User] = Depends(get_current_user)):
    """
    Guarantees that demo endpoints cannot be executed anonymously in production.
    In development with DEMO_MODE=True, access is permitted.
    In production or when DEMO_MODE=False, access is restricted to authenticated reviewers.
    """
    if settings.DEMO_MODE and not settings.is_production:
        return True
    if user and (user.id.startswith("reviewer_") or user.phone_number in [
        getattr(settings, "REVIEWER_PHONE", None), "9988776655", "+919988776655"
    ]):
        return True
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Demo mode and scenarios are disabled in production. Access is restricted to authenticated reviewers."
    )


router = APIRouter(prefix="/demo", tags=["Demo Mode & Scenarios"], dependencies=[Depends(verify_demo_access)])


class ScenarioExecuteRequest(BaseModel):
    scenario_id: int
    language: str = "en"


@router.get("/profile")
async def get_demo_profile():
    """
    Returns the canonical demonstration farmer & farm digital twin.
    Labeled explicitly as DEMO_PROFILE / SIMULATED.
    """
    return DemoModeService.get_demo_profile()


@router.post("/reset")
async def reset_demo_state():
    """
    Resets demo farm tasks, conversation memory, and confirmation states
    to the pristine demonstration baseline for live presentation.
    """
    return DemoModeService.reset_demo_state()


@router.get("/scenarios")
async def list_demo_scenarios():
    """
    Returns the catalog of 11 live presentation demonstration scenarios.
    """
    return {
        "data_mode": DemoModeService.DATA_LABEL,
        "scenarios": DemoModeService.get_demo_scenarios()
    }


@router.post("/scenarios/{scenario_id}/execute")
async def execute_demo_scenario(scenario_id: int, language: str = Query(default="en")):
    """
    Executes a demonstration scenario deterministically through the orchestrator.
    """
    if scenario_id < 1 or scenario_id > 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario_id {scenario_id}. Must be between 1 and 11."
        )
    return await DemoModeService.execute_scenario(scenario_id=scenario_id, language=language)

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from app.services.demo.demo_service import DemoModeService

router = APIRouter(prefix="/demo", tags=["Demo Mode & Scenarios"])


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

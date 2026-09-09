from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.memory.digital_twin import DigitalTwinService
from app.services.crop.comparison_service import CropComparisonService, CropComparisonResponse
from app.repositories.farm_repo import FarmRepository
from app.repositories.task_repo import TaskRepository
from app.schemas.task import FarmTaskResponse, FarmTaskCreate

router = APIRouter(prefix="/farm", tags=["Farm Digital Twin & Management"])

@router.get("/summary")
async def get_farm_summary(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get full Digital Twin summary for the active farmer.
    """
    context = await DigitalTwinService.get_farmer_context(db, user_id)
    return {
        "status": "success",
        "farmer": context.to_dict(),
        "prompt_context": context.to_prompt_context()
    }

@router.get("/crops")
async def get_farm_crops(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get all active crops and lifecycle stages.
    """
    farm_repo = FarmRepository(db)
    farms = await farm_repo.get_farms_by_farmer(user_id)
    crops = []
    for f in farms:
        for c in f.crops:
            crops.append({
                "id": c.id,
                "crop_name": c.crop_name,
                "variety": c.variety,
                "area_acres": float(c.area_acres),
                "current_stage": c.current_stage,
                "status": c.status,
                "sowing_date": str(c.sowing_date) if c.sowing_date else None,
                "expected_harvest_date": str(c.expected_harvest_date) if c.expected_harvest_date else None
            })
    return {"status": "success", "crops": crops}

@router.get("/tasks")
async def get_farm_tasks(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get dynamic scheduled farm tasks.
    """
    task_repo = TaskRepository(db)
    tasks = await task_repo.get_tasks_by_farmer(user_id)
    return {"status": "success", "tasks": [FarmTaskResponse.model_validate(t) for t in tasks]}

@router.post("/compare-crops", response_model=CropComparisonResponse)
async def compare_crops(
    crops: List[str],
    area_acres: float = 3.0,
    soil_type: str = "black",
    location: str = "Guntur"
):
    """
    Side-by-side multi-crop comparison across yield, revenue, costs, net profit, and risk.
    """
    return CropComparisonService.compare_crops(
        crop_names=crops,
        area_acres=Decimal(str(area_acres)),
        soil_type=soil_type,
        location=location
    )

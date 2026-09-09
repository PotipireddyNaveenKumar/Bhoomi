from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.repositories.task_repo import TaskRepository
from app.schemas.task import (
    FarmTaskCreate,
    FarmTaskUpdate,
    FarmTaskResponse,
    FarmTask,
    TaskStatus
)
from app.services.tasks.smart_reminder_engine import SmartReminderEngine
from app.services.weather.weather_service import WeatherService
from app.services.farm_manager.state_engine import FarmStateEngine
from app.services.farm_manager.task_engine import TaskIntelligenceEngine

router = APIRouter(prefix="/tasks", tags=["Farm Tasks & Smart Reminders"])


class TaskActionRequest(BaseModel):
    farmer_id: str = "farmer_demo_1"
    farm_id: str = "farm_1"
    reason: Optional[str] = None
    days_to_postpone: int = 2
    completion_source: str = "api"


# --- Canonical Phase 6 Step 2 Task Endpoints ---

@router.get("/today", response_model=List[FarmTask])
async def get_today_tasks(
    farmer_id: str = Query(default="farmer_demo_1"),
    farm_id: str = Query(default="farm_1"),
    db: AsyncSession = Depends(get_db)
):
    """
    Answers: "What should I do today?"
    Returns prioritized canonical FarmTasks due today or needing immediate attention.
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, db=db)
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    today_str = datetime.now(timezone.utc).date().isoformat()
    return [t for t in tasks if t.due_at[:10] == today_str or t.status in [TaskStatus.DUE, TaskStatus.POSTPONED]]


@router.get("/week", response_model=List[FarmTask])
async def get_week_tasks(
    farmer_id: str = Query(default="farmer_demo_1"),
    farm_id: str = Query(default="farm_1"),
    db: AsyncSession = Depends(get_db)
):
    """
    Answers: "What should I do this week?"
    Returns a 7-day scheduled view of canonical FarmTasks.
    """
    state = await FarmStateEngine.get_current_state(farmer_id=farmer_id, db=db)
    return TaskIntelligenceEngine.generate_tasks_for_farm(state)


@router.post("/{task_id}/complete", response_model=FarmTask)
async def complete_farm_task(
    task_id: str,
    payload: Optional[TaskActionRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Marks a task as COMPLETED, records timestamps and logs to FarmMemoryV2 and DB.
    """
    req = payload or TaskActionRequest()
    try:
        t = TaskIntelligenceEngine.complete_task(
            task_id=task_id,
            farmer_id=req.farmer_id,
            farm_id=req.farm_id,
            completion_source=req.completion_source
        )
        try:
            repo = TaskRepository(db)
            await repo.update_task(task_id, req.farmer_id, FarmTaskUpdate(status="completed"))
        except Exception:
            pass
        return t
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{task_id}/postpone", response_model=FarmTask)
async def postpone_farm_task(
    task_id: str,
    payload: TaskActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Postpones a task with reasoned justification and logs to FarmMemoryV2 and DB.
    """
    try:
        t = TaskIntelligenceEngine.postpone_task(
            task_id=task_id,
            farmer_id=payload.farmer_id,
            reason=payload.reason or "Postponed via user request",
            days_to_postpone=payload.days_to_postpone,
            farm_id=payload.farm_id
        )
        try:
            repo = TaskRepository(db)
            await repo.update_task(task_id, payload.farmer_id, FarmTaskUpdate(status="postponed", reason=payload.reason))
        except Exception:
            pass
        return t
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{task_id}/skip", response_model=FarmTask)
async def skip_farm_task(
    task_id: str,
    payload: Optional[TaskActionRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Skips a task and logs to FarmMemoryV2 and DB.
    """
    req = payload or TaskActionRequest()
    try:
        t = TaskIntelligenceEngine.skip_task(
            task_id=task_id,
            farmer_id=req.farmer_id,
            reason=req.reason or "Skipped via user request",
            farm_id=req.farm_id
        )
        try:
            repo = TaskRepository(db)
            await repo.update_task(task_id, req.farmer_id, FarmTaskUpdate(status="cancelled", reason=req.reason))
        except Exception:
            pass
        return t
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Legacy / DB-backed task endpoints (preserved for backwards compatibility) ---

@router.get("", response_model=List[FarmTaskResponse])
async def get_tasks(
    status_filter: Optional[str] = Query(default=None),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = TaskRepository(db)
    return await repo.get_tasks_by_farmer(farmer.id, status=status_filter)


@router.post("", response_model=FarmTaskResponse)
async def create_task(
    task_in: FarmTaskCreate,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = TaskRepository(db)
    return await repo.create_task(farmer.id, task_in, source="user")


@router.put("/{task_id}", response_model=FarmTaskResponse)
async def update_task(
    task_id: str,
    update_in: FarmTaskUpdate,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = TaskRepository(db)
    task = await repo.update_task(task_id, farmer.id, update_in)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


@router.post("/{task_id}/evaluate-condition")
async def evaluate_smart_reminder(
    task_id: str,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluates condition-based reminders before firing alarms:
    DO, POSTPONE, MODIFY, or CANCEL.
    """
    repo = TaskRepository(db)
    tasks = await repo.get_tasks_by_farmer(farmer.id)
    target_task = next((t for t in tasks if t.id == task_id), None)
    if not target_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    weather = await WeatherService.get_weather(location=farmer.district or "Guntur")
    action = SmartReminderEngine.evaluate_task_conditions(target_task, weather.current.model_dump())

    return {
        "task_id": task_id,
        "task_title": target_task.title,
        "recommended_action": action.action,
        "reason": action.reason,
        "scheduled_date": action.adjusted_date
    }


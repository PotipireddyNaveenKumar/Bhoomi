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
    farm_id: Optional[str] = None
    reason: Optional[str] = None
    days_to_postpone: int = 2
    completion_source: str = "api"


async def _resolve_and_verify_task_ownership(
    task_id: str,
    requested_farm_id: Optional[str],
    farmer: FarmerProfile,
    db: AsyncSession
) -> str:
    """
    Verifies that task_id belongs to an authorized farm of the authenticated farmer.
    Returns target_farm_id.
    Raises 403 Forbidden or 404 Not Found if unauthorized or missing.
    """
    from app.repositories.farm_repo import FarmRepository
    farm_repo = FarmRepository(db)
    farms = await farm_repo.get_farms_by_farmer(farmer.id)
    authorized_farm_ids = [f.id for f in farms] if farms else []

    if requested_farm_id:
        if requested_farm_id not in authorized_farm_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Specified farm does not belong to the authenticated farmer."
            )
        search_farms = [requested_farm_id]
    else:
        search_farms = authorized_farm_ids

    # 1. Search in TaskIntelligenceEngine active memory under farmer's authorized farms
    for fid in search_farms:
        for t in TaskIntelligenceEngine.get_tasks_for_farm(fid):
            if t.task_id == task_id:
                return fid

    # 2. Check if task exists in DB
    repo = TaskRepository(db)
    db_task = await repo.get_task_by_id(task_id)
    if db_task:
        if db_task.farmer_id != farmer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not own this task."
            )
        farm_id_for_db = getattr(db_task, "farm_id", None) or (search_farms[0] if search_farms else "farm_1")
        return farm_id_for_db

    # 3. Check if task belongs to any other farm in memory (cross-tenant leak detection)
    for fid, f_tasks in TaskIntelligenceEngine._tasks_by_farm.items():
        if any(t.task_id == task_id for t in f_tasks):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not own this task."
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with ID {task_id} not found."
    )


# --- Canonical Phase 6 Step 2 Task Endpoints (Strictly Authenticated) ---

@router.get("/today", response_model=List[FarmTask])
async def get_today_tasks(
    farm_id: Optional[str] = Query(default=None),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Answers: "What should I do today?"
    Returns prioritized canonical FarmTasks due today strictly for the authenticated farmer.
    """
    from app.repositories.farm_repo import FarmRepository
    farm_repo = FarmRepository(db)
    farms = await farm_repo.get_farms_by_farmer(farmer.id)
    if not farms:
        return []

    authorized_farm_ids = [f.id for f in farms]
    target_farm_id = farm_id or authorized_farm_ids[0]
    if target_farm_id not in authorized_farm_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Specified farm does not belong to the authenticated farmer."
        )

    state = await FarmStateEngine.get_current_state(farmer_id=farmer.id, db=db)
    state.farm_id = target_farm_id
    tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    today_str = datetime.now(timezone.utc).date().isoformat()
    return [t for t in tasks if t.due_at[:10] == today_str or t.status in [TaskStatus.DUE, TaskStatus.POSTPONED]]


@router.get("/week", response_model=List[FarmTask])
async def get_week_tasks(
    farm_id: Optional[str] = Query(default=None),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Answers: "What should I do this week?"
    Returns a 7-day scheduled view of canonical FarmTasks strictly for the authenticated farmer.
    """
    from app.repositories.farm_repo import FarmRepository
    farm_repo = FarmRepository(db)
    farms = await farm_repo.get_farms_by_farmer(farmer.id)
    if not farms:
        return []

    authorized_farm_ids = [f.id for f in farms]
    target_farm_id = farm_id or authorized_farm_ids[0]
    if target_farm_id not in authorized_farm_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Specified farm does not belong to the authenticated farmer."
        )

    state = await FarmStateEngine.get_current_state(farmer_id=farmer.id, db=db)
    state.farm_id = target_farm_id
    return TaskIntelligenceEngine.generate_tasks_for_farm(state)


@router.post("/{task_id}/complete", response_model=FarmTask)
async def complete_farm_task(
    task_id: str,
    payload: Optional[TaskActionRequest] = None,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Marks a task as COMPLETED, records timestamps and logs to FarmMemoryV2 and DB.
    Enforces strict authenticated farmer tenant ownership.
    """
    req = payload or TaskActionRequest()
    target_farm_id = await _resolve_and_verify_task_ownership(
        task_id=task_id,
        requested_farm_id=req.farm_id,
        farmer=farmer,
        db=db
    )
    try:
        t = TaskIntelligenceEngine.complete_task(
            task_id=task_id,
            farmer_id=farmer.id,
            farm_id=target_farm_id,
            completion_source=req.completion_source or "api"
        )
        try:
            repo = TaskRepository(db)
            await repo.update_task(task_id, farmer.id, FarmTaskUpdate(status="completed"))
        except Exception:
            pass
        return t
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{task_id}/postpone", response_model=FarmTask)
async def postpone_farm_task(
    task_id: str,
    payload: Optional[TaskActionRequest] = None,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Postpones a task with reasoned justification and logs to FarmMemoryV2 and DB.
    Enforces strict authenticated farmer tenant ownership.
    """
    req = payload or TaskActionRequest()
    target_farm_id = await _resolve_and_verify_task_ownership(
        task_id=task_id,
        requested_farm_id=req.farm_id,
        farmer=farmer,
        db=db
    )
    try:
        t = TaskIntelligenceEngine.postpone_task(
            task_id=task_id,
            farmer_id=farmer.id,
            reason=req.reason or "Postponed via user request",
            days_to_postpone=req.days_to_postpone,
            farm_id=target_farm_id
        )
        try:
            repo = TaskRepository(db)
            await repo.update_task(task_id, farmer.id, FarmTaskUpdate(status="postponed", reason=req.reason))
        except Exception:
            pass
        return t
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{task_id}/skip", response_model=FarmTask)
async def skip_farm_task(
    task_id: str,
    payload: Optional[TaskActionRequest] = None,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Skips a task and logs to FarmMemoryV2 and DB.
    Enforces strict authenticated farmer tenant ownership.
    """
    req = payload or TaskActionRequest()
    target_farm_id = await _resolve_and_verify_task_ownership(
        task_id=task_id,
        requested_farm_id=req.farm_id,
        farmer=farmer,
        db=db
    )
    try:
        t = TaskIntelligenceEngine.skip_task(
            task_id=task_id,
            farmer_id=farmer.id,
            reason=req.reason or "Skipped via user request",
            farm_id=target_farm_id
        )
        try:
            repo = TaskRepository(db)
            await repo.update_task(task_id, farmer.id, FarmTaskUpdate(status="cancelled", reason=req.reason))
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


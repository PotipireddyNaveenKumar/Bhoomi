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
    TaskStatus,
    TaskType
)
from app.schemas.decision import DecisionPriority
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
    SQL farm_tasks table is the authoritative persistent state.
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
    ai_tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
    today_date = datetime.now(timezone.utc).date()
    today_str = today_date.isoformat()

    # Query persistent tasks from SQL database
    repo = TaskRepository(db)
    db_tasks = await repo.get_tasks_by_farmer(farmer.id)
    db_status_map = {t.id: t.status for t in db_tasks}
    db_title_map = {t.title.lower(): t.status for t in db_tasks}

    filtered_tasks: List[FarmTask] = []
    seen_task_ids = set()

    # 1. Include AI generated tasks, applying DB completion status if completed
    for t in ai_tasks:
        if t.due_at[:10] == today_str or t.status in [TaskStatus.DUE, TaskStatus.POSTPONED, TaskStatus.COMPLETED]:
            if db_status_map.get(t.task_id) == "completed" or db_title_map.get(t.title.lower()) == "completed":
                t.status = TaskStatus.COMPLETED
                t.completion_status = "SUCCESS"
            filtered_tasks.append(t)
            seen_task_ids.add(t.task_id)
            seen_task_ids.add(t.title.lower())

    # 2. Include SQL DB tasks due today or pending/completed today
    for dbt in db_tasks:
        if dbt.id in seen_task_ids or dbt.title.lower() in seen_task_ids:
            continue
        dbt_farm_id = dbt.farm_id or target_farm_id
        if dbt_farm_id != target_farm_id:
            continue
        due_str = str(dbt.due_date) if dbt.due_date else today_str
        is_today = (due_str == today_str) or (dbt.due_date and dbt.due_date <= today_date and dbt.status in ["pending", "in_progress", "due", "completed"])
        if is_today:
            status_enum = TaskStatus.COMPLETED if dbt.status == "completed" else TaskStatus.DUE
            ft = FarmTask(
                task_id=dbt.id,
                farm_id=dbt_farm_id,
                crop=getattr(dbt, "crop", None) or state.active_crop or "General",
                task_type=TaskType.IRRIGATION if "irrig" in (dbt.task_type or "").lower() else TaskType.GENERAL_FARM_TASK,
                title=dbt.title,
                description=dbt.description,
                priority=DecisionPriority.HIGH if (dbt.priority or "").lower() == "high" else DecisionPriority.MEDIUM,
                status=status_enum,
                due_at=due_str,
                trigger="farm_schedule",
                reason=dbt.reason or "Scheduled task from farm plan",
                completion_status="SUCCESS" if dbt.status == "completed" else None
            )
            filtered_tasks.append(ft)
            seen_task_ids.add(dbt.id)

    return filtered_tasks


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
    Authoritative persistence is the SQL farm_tasks table.
    """
    req = payload or TaskActionRequest()
    target_farm_id = await _resolve_and_verify_task_ownership(
        task_id=task_id,
        requested_farm_id=req.farm_id,
        farmer=farmer,
        db=db
    )
    now_str = datetime.now(timezone.utc).isoformat()
    repo = TaskRepository(db)
    db_task = await repo.get_task_by_id(task_id)

    from app.services.memory.farm_memory_v2 import FarmMemoryV2

    # 1. If task exists in SQL DB:
    if db_task:
        await repo.update_task(task_id, farmer.id, FarmTaskUpdate(status="completed"))
        FarmMemoryV2.add_memory(
            farmer_id=farmer.id,
            category="EVENT",
            key=f"task_completed_{task_id}",
            value={
                "task_id": task_id,
                "title": db_task.title,
                "farm_id": target_farm_id,
                "completed_at": now_str,
                "completion_source": req.completion_source or "api"
            },
            source=req.completion_source or "api"
        )
        # Update TaskIntelligenceEngine in-memory if present
        for t in TaskIntelligenceEngine.get_tasks_for_farm(target_farm_id):
            if t.task_id == task_id or t.title.lower() == db_task.title.lower():
                t.status = TaskStatus.COMPLETED
                t.completion_status = "SUCCESS"
                t.completed_at = now_str
                t.completion_source = req.completion_source or "api"
                return t

        return FarmTask(
            task_id=db_task.id,
            farm_id=target_farm_id,
            crop="General",
            task_type=TaskType.IRRIGATION if "irrig" in (db_task.task_type or "").lower() else TaskType.GENERAL_FARM_TASK,
            title=db_task.title,
            description=db_task.description,
            priority=DecisionPriority.MEDIUM,
            status=TaskStatus.COMPLETED,
            due_at=str(db_task.due_date),
            trigger="user_schedule",
            reason=db_task.reason or "Scheduled task completed by farmer",
            completion_status="SUCCESS",
            completed_at=now_str,
            completion_source=req.completion_source or "api"
        )

    # 2. If task exists in TaskIntelligenceEngine in-memory:
    in_memory_task = None
    for t in TaskIntelligenceEngine.get_tasks_for_farm(target_farm_id):
        if t.task_id == task_id:
            in_memory_task = t
            break

    if in_memory_task:
        if in_memory_task.status == TaskStatus.COMPLETED:
            return in_memory_task

        t = TaskIntelligenceEngine.complete_task(
            task_id=task_id,
            farmer_id=farmer.id,
            farm_id=target_farm_id,
            completion_source=req.completion_source or "api"
        )
        # Persist to SQL farm_tasks as authoritative record
        try:
            from datetime import date
            due_d = date.today()
            if t.due_at:
                try:
                    due_d = date.fromisoformat(t.due_at[:10])
                except Exception:
                    pass
            new_db_task = await repo.create_task(
                farmer_id=farmer.id,
                task_in=FarmTaskCreate(
                    farm_id=target_farm_id,
                    title=t.title,
                    description=t.description,
                    task_type=t.task_type.value if hasattr(t.task_type, "value") else str(t.task_type),
                    due_date=due_d,
                    reason=t.reason
                ),
                source=req.completion_source or "ai_agent"
            )
            await repo.update_task(new_db_task.id, farmer.id, FarmTaskUpdate(status="completed"))
        except Exception:
            pass

        return t

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with ID {task_id} not found."
    )



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


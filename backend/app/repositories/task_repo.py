from typing import Optional, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.task import FarmTask, TaskStatus
from app.schemas.task import FarmTaskCreate, FarmTaskUpdate

class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tasks_by_farmer(self, farmer_id: str, status: Optional[str] = None) -> List[FarmTask]:
        query = select(FarmTask).where(FarmTask.farmer_id == farmer_id)
        if status:
            query = query.where(FarmTask.status == status)
        query = query.order_by(FarmTask.due_date.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_task(self, farmer_id: str, task_in: FarmTaskCreate, source: str = "ai_agent") -> FarmTask:
        task = FarmTask(
            farmer_id=farmer_id,
            farm_id=task_in.farm_id,
            crop_id=task_in.crop_id,
            title=task_in.title,
            description=task_in.description,
            task_type=task_in.task_type,
            priority=task_in.priority,
            status=TaskStatus.PENDING.value,
            due_date=task_in.due_date,
            reason=task_in.reason,
            conditions=task_in.conditions,
            source=source,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update_task(self, task_id: str, farmer_id: str, update_in: FarmTaskUpdate) -> Optional[FarmTask]:
        result = await self.db.execute(
            select(FarmTask).where(FarmTask.id == task_id, FarmTask.farmer_id == farmer_id)
        )
        task = result.scalars().first()
        if not task:
            return None
        if update_in.title is not None:
            task.title = update_in.title
        if update_in.description is not None:
            task.description = update_in.description
        if update_in.priority is not None:
            task.priority = update_in.priority
        if update_in.status is not None:
            task.status = update_in.status
        if update_in.due_date is not None:
            task.due_date = update_in.due_date
        if update_in.reason is not None:
            task.reason = update_in.reason
        if update_in.conditions is not None:
            task.conditions = update_in.conditions
        await self.db.commit()
        await self.db.refresh(task)
        return task

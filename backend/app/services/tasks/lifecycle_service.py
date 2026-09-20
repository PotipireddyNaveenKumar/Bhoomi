import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, update

from app.models.task import FarmTask, TaskStatus
from app.core.datetime_utils import utc_now_naive
from app.services.memory.farm_memory_v2 import FarmMemoryV2, ProvenanceType

logger = logging.getLogger("bhoomi.tasks.lifecycle")


class TaskTransitionRecord(BaseModel):
    task_id: str
    title: str
    previous_status: str
    new_status: str
    timestamp: str
    reason: Optional[str] = None


class TaskLifecycleRunResult(BaseModel):
    success: bool = True
    timestamp: str
    tasks_scanned: int = 0
    tasks_transitioned: int = 0
    tasks_failed: int = 0
    transitions: List[TaskTransitionRecord] = Field(default_factory=list)


class TaskLifecycleService:
    """
    Production Proactive Farm Task Lifecycle Engine.
    Operates on PostgreSQL authoritative farm_tasks table.
    
    Lifecycle States:
      PENDING / SCHEDULED -> DUE -> OVERDUE -> EXPIRED -> COMPLETED / CANCELLED / POSTPONED
      
    Guarantees:
      1. Concurrency safe (SELECT FOR UPDATE SKIP LOCKED on PostgreSQL)
      2. Timezone-aware UTC evaluation
      3. Completed & cancelled tasks are strictly immutable
      4. Idempotent execution (repeated runs produce no duplicate transitions or events)
      5. Emits compact, deduplicated FarmMemoryV2 events
      6. Preserves tenant ownership
    """

    OVERDUE_THRESHOLD = timedelta(hours=6)

    @classmethod
    async def reap_and_transition_tasks(
        cls,
        db: AsyncSession,
        farmer_id: Optional[str] = None,
        farm_id: Optional[str] = None,
        reference_now: Optional[datetime] = None
    ) -> TaskLifecycleRunResult:
        """
        Scans active tasks and executes deterministic lifecycle transitions.
        """
        now = reference_now if reference_now is not None else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        result = TaskLifecycleRunResult(
            timestamp=now.isoformat(),
            tasks_scanned=0,
            tasks_transitioned=0,
            tasks_failed=0,
            transitions=[]
        )

        try:
            # Active non-terminal statuses
            active_statuses = [
                TaskStatus.PENDING.value,
                TaskStatus.SCHEDULED.value,
                "planned",
                TaskStatus.DUE.value,
                TaskStatus.IN_PROGRESS.value,
                TaskStatus.OVERDUE.value
            ]

            query = select(FarmTask).where(FarmTask.status.in_(active_statuses))
            if farmer_id:
                query = query.where(FarmTask.farmer_id == farmer_id)
            if farm_id:
                query = query.where(FarmTask.farm_id == farm_id)

            # PostgreSQL concurrency safety: lock rows and skip currently locked rows
            is_postgres = False
            bind = getattr(db, "bind", None)
            if bind and hasattr(bind, "dialect"):
                is_postgres = "postgres" in bind.dialect.name.lower()
            elif hasattr(db, "connection"):
                # AsyncSession check
                is_postgres = True

            if is_postgres:
                try:
                    query = query.with_for_update(skip_locked=True)
                except Exception:
                    pass

            db_result = await db.execute(query)
            tasks = list(db_result.scalars().all())
            result.tasks_scanned = len(tasks)

            for task in tasks:
                prev_status = (task.status or "pending").lower()

                # Immutable terminal statuses guard
                if prev_status in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value, "skipped"]:
                    continue

                # Parse timezone-aware due_at
                due_dt: Optional[datetime] = None
                if task.due_at:
                    due_dt = task.due_at
                    if due_dt.tzinfo is None:
                        due_dt = due_dt.replace(tzinfo=timezone.utc)
                elif task.due_date:
                    # Fallback to due_date: interpreted at 18:00 UTC (evening of due date)
                    due_dt = datetime(
                        task.due_date.year,
                        task.due_date.month,
                        task.due_date.day,
                        18, 0, 0,
                        tzinfo=timezone.utc
                    )

                # Parse timezone-aware expires_at
                exp_dt: Optional[datetime] = None
                if task.expires_at:
                    exp_dt = task.expires_at
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)

                new_status = prev_status
                event_type: Optional[str] = None
                event_reason: Optional[str] = None

                # 1. Check EXPIRED
                if exp_dt and now >= exp_dt:
                    if prev_status != TaskStatus.EXPIRED.value:
                        new_status = TaskStatus.EXPIRED.value
                        event_type = "EXPIRED"
                        event_reason = f"Task validity expired at {exp_dt.isoformat()}"

                # 2. Check OVERDUE
                elif due_dt and now > (due_dt + cls.OVERDUE_THRESHOLD):
                    if prev_status not in [TaskStatus.OVERDUE.value, TaskStatus.EXPIRED.value]:
                        new_status = TaskStatus.OVERDUE.value
                        event_type = "OVERDUE"
                        event_reason = f"Task overdue past due threshold ({due_dt.isoformat()})"

                # 3. Check DUE
                elif due_dt and now >= due_dt:
                    if prev_status in [TaskStatus.PENDING.value, TaskStatus.SCHEDULED.value, "planned"]:
                        new_status = TaskStatus.DUE.value
                        event_type = "DUE"
                        event_reason = f"Task reached scheduled due time ({due_dt.isoformat()})"

                # 4. Apply transition if status changed
                if new_status != prev_status:
                    # Atomic conditional update prevents concurrent race conditions
                    update_stmt = (
                        update(FarmTask)
                        .where(FarmTask.id == task.id, FarmTask.status == prev_status)
                        .values(status=new_status, updated_at=utc_now_naive())
                    )
                    update_res = await db.execute(update_stmt)
                    if update_res.rowcount == 0:
                        # Another worker or transaction already transitioned this task
                        continue

                    task.status = new_status
                    task.updated_at = utc_now_naive()

                    transition = TaskTransitionRecord(
                        task_id=task.id,
                        title=task.title,
                        previous_status=prev_status,
                        new_status=new_status,
                        timestamp=now.isoformat(),
                        reason=event_reason
                    )
                    result.transitions.append(transition)
                    result.tasks_transitioned += 1

                    # Emit compact deduplicated FarmMemoryV2 event
                    if event_type:
                        event_key = f"task_{event_type.lower()}_{task.id}"
                        existing_keys = {m.key for m in FarmMemoryV2._store.get(task.farmer_id, [])}
                        if event_key not in existing_keys:
                            try:
                                FarmMemoryV2.add_memory(
                                    farmer_id=task.farmer_id,
                                    category="EVENT",
                                    key=event_key,
                                    value={
                                        "task_id": task.id,
                                        "title": task.title,
                                        "task_type": task.task_type,
                                        "farm_id": task.farm_id,
                                        "previous_status": prev_status,
                                        "new_status": new_status,
                                        "due_at": due_dt.isoformat() if due_dt else None,
                                        "timestamp": now.isoformat(),
                                        "reason": event_reason
                                    },
                                    confidence=1.0,
                                    source="task_lifecycle_engine",
                                    provenance=ProvenanceType.SYSTEM_RECOMMENDATION
                                )
                            except Exception as e:
                                logger.debug(f"FarmMemoryV2 lifecycle logging skipped: {e}")

            await db.commit()
            logger.info(
                "TASK_LIFECYCLE_RUN tasks_scanned=%d tasks_transitioned=%d tasks_failed=%d",
                result.tasks_scanned,
                result.tasks_transitioned,
                result.tasks_failed
            )

        except Exception as e:
            await db.rollback()
            result.success = False
            result.tasks_failed += 1
            logger.error(f"TASK_LIFECYCLE_RUN_FAILED: {e}", exc_info=True)
            raise

        return result

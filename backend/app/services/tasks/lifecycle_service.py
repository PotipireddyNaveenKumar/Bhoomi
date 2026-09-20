import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, update

from app.models.task import FarmTask, TaskStatus
from app.models.task_event import FarmTaskEvent, TaskEventType, TaskEventStatus
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
      7. Durable event records in farm_task_events with deterministic uniqueness
    """

    OVERDUE_THRESHOLD = timedelta(hours=6)
    REMINDER_LEAD_TIME = timedelta(hours=2)

    @classmethod
    async def _record_task_event(
        cls,
        db: AsyncSession,
        task: FarmTask,
        event_type: str,
        event_key: str,
        scheduled_for: Optional[datetime] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Durable task event recording with database-level uniqueness deduplication.
        Returns True if a new event was created, False if already exists.
        """
        try:
            # Check existing event by unique event_key
            existing_stmt = select(FarmTaskEvent.id).where(FarmTaskEvent.event_key == event_key)
            existing_res = await db.execute(existing_stmt)
            if existing_res.scalar_one_or_none() is not None:
                return False

            new_event = FarmTaskEvent(
                id=str(uuid.uuid4()),
                task_id=task.id,
                farmer_id=task.farmer_id,
                farm_id=task.farm_id,
                event_type=event_type,
                event_key=event_key,
                scheduled_for=scheduled_for,
                payload=payload or {},
                status=TaskEventStatus.PENDING.value
            )
            db.add(new_event)

            # Compact deduplicated FarmMemoryV2 event
            existing_keys = {m.key for m in FarmMemoryV2._store.get(task.farmer_id, [])}
            if event_key not in existing_keys:
                try:
                    mem_val = {
                        "task_id": task.id,
                        "title": task.title,
                        "task_type": getattr(task, "task_type", "general"),
                        "farm_id": task.farm_id,
                        "event_type": event_type,
                        "due_at": scheduled_for.isoformat() if scheduled_for else None,
                    }
                    if payload:
                        mem_val.update(payload)
                    FarmMemoryV2.add_memory(
                        farmer_id=task.farmer_id,
                        category="EVENT",
                        key=event_key,
                        value=mem_val,
                        confidence=1.0,
                        source="task_lifecycle_engine",
                        provenance=ProvenanceType.SYSTEM_RECOMMENDATION
                    )
                except Exception as mem_err:
                    logger.debug(f"FarmMemoryV2 event logging skipped: {mem_err}")

            return True
        except Exception as e:
            logger.warning(f"Error persisting task event {event_key}: {e}")
            return False

    @classmethod
    async def reap_and_transition_tasks(
        cls,
        db: AsyncSession,
        farmer_id: Optional[str] = None,
        farm_id: Optional[str] = None,
        reference_now: Optional[datetime] = None
    ) -> TaskLifecycleRunResult:
        """
        Farmer-scoped task reaper.
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

            is_postgres = False
            bind = getattr(db, "bind", None)
            if bind and hasattr(bind, "dialect"):
                is_postgres = "postgres" in bind.dialect.name.lower()
            elif hasattr(db, "connection"):
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

                due_dt: Optional[datetime] = None
                if task.due_at:
                    due_dt = task.due_at
                    if due_dt.tzinfo is None:
                        due_dt = due_dt.replace(tzinfo=timezone.utc)
                elif task.due_date:
                    due_dt = datetime(
                        task.due_date.year,
                        task.due_date.month,
                        task.due_date.day,
                        18, 0, 0,
                        tzinfo=timezone.utc
                    )

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
                        event_type = TaskEventType.TASK_EXPIRED.value
                        event_reason = f"Task validity expired at {exp_dt.isoformat()}"

                # 2. Check OVERDUE
                elif due_dt and now > (due_dt + cls.OVERDUE_THRESHOLD):
                    if prev_status not in [TaskStatus.OVERDUE.value, TaskStatus.EXPIRED.value]:
                        new_status = TaskStatus.OVERDUE.value
                        event_type = TaskEventType.TASK_OVERDUE.value
                        event_reason = f"Task overdue past due threshold ({due_dt.isoformat()})"

                # 3. Check DUE
                elif due_dt and now >= due_dt:
                    if prev_status in [TaskStatus.PENDING.value, TaskStatus.SCHEDULED.value, "planned"]:
                        new_status = TaskStatus.DUE.value
                        event_type = TaskEventType.TASK_DUE.value
                        event_reason = f"Task reached scheduled due time ({due_dt.isoformat()})"

                # 4. Apply transition if status changed
                if new_status != prev_status:
                    update_stmt = (
                        update(FarmTask)
                        .where(FarmTask.id == task.id, FarmTask.status == prev_status)
                        .values(status=new_status, updated_at=utc_now_naive())
                    )
                    update_res = await db.execute(update_stmt)
                    if update_res.rowcount == 0:
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

                    # Persist durable event
                    if event_type:
                        event_key = f"task_{event_type.lower().replace('task_', '')}_{task.id}"
                        await cls._record_task_event(
                            db=db,
                            task=task,
                            event_type=event_type,
                            event_key=event_key,
                            scheduled_for=due_dt or exp_dt,
                            payload={
                                "task_id": task.id,
                                "title": task.title,
                                "previous_status": prev_status,
                                "new_status": new_status,
                                "reason": event_reason,
                                "timestamp": now.isoformat()
                            }
                        )

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

    @classmethod
    async def run_global_lifecycle(
        cls,
        db: AsyncSession,
        reference_now: Optional[datetime] = None,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Global Proactive Task Lifecycle Runner.
        Scans all farms and farmers in bounded batches using PostgreSQL row locks.
        Emits durable lifecycle and reminder events.
        
        Guarantees:
          - Bounded memory via keyset pagination (WHERE id > last_seen_id LIMIT batch_size)
          - Commit per batch (avoids long locks and huge transactions)
          - PostgreSQL SELECT ... FOR UPDATE SKIP LOCKED
          - Preserves tenant ownership (farmer_id and farm_id)
          - Deduplicated events in farm_task_events
          - Safe isolation: errors on individual tasks do not stop other tasks
        """
        now = reference_now if reference_now is not None else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        stats: Dict[str, int] = {
            "tasks_scanned": 0,
            "tasks_transitioned": 0,
            "due": 0,
            "overdue": 0,
            "expired": 0,
            "reminders_created": 0,
            "failed": 0
        }

        active_statuses = [
            TaskStatus.PENDING.value,
            TaskStatus.SCHEDULED.value,
            "planned",
            TaskStatus.DUE.value,
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.OVERDUE.value
        ]

        is_postgres = False
        bind = getattr(db, "bind", None)
        if bind and hasattr(bind, "dialect"):
            is_postgres = "postgres" in bind.dialect.name.lower()
        elif hasattr(db, "connection"):
            is_postgres = True

        last_id = ""

        while True:
            try:
                query = (
                    select(FarmTask)
                    .where(FarmTask.status.in_(active_statuses))
                    .where(FarmTask.id > last_id)
                    .order_by(FarmTask.id.asc())
                    .limit(batch_size)
                )

                if is_postgres:
                    try:
                        query = query.with_for_update(skip_locked=True)
                    except Exception:
                        pass

                batch_res = await db.execute(query)
                batch_tasks = list(batch_res.scalars().all())

                if not batch_tasks:
                    break

                last_id = batch_tasks[-1].id
                stats["tasks_scanned"] += len(batch_tasks)

                for task in batch_tasks:
                    try:
                        prev_status = (task.status or "pending").lower()

                        # Terminal immutable safety
                        if prev_status in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value, "skipped"]:
                            continue

                        due_dt: Optional[datetime] = None
                        if task.due_at:
                            due_dt = task.due_at
                            if due_dt.tzinfo is None:
                                due_dt = due_dt.replace(tzinfo=timezone.utc)
                        elif task.due_date:
                            due_dt = datetime(
                                task.due_date.year,
                                task.due_date.month,
                                task.due_date.day,
                                18, 0, 0,
                                tzinfo=timezone.utc
                            )

                        exp_dt: Optional[datetime] = None
                        if task.expires_at:
                            exp_dt = task.expires_at
                            if exp_dt.tzinfo is None:
                                exp_dt = exp_dt.replace(tzinfo=timezone.utc)

                        new_status = prev_status
                        event_type: Optional[str] = None
                        event_reason: Optional[str] = None

                        # 1. EXPIRED
                        if exp_dt and now >= exp_dt:
                            if prev_status != TaskStatus.EXPIRED.value:
                                new_status = TaskStatus.EXPIRED.value
                                event_type = TaskEventType.TASK_EXPIRED.value
                                event_reason = f"Task validity expired at {exp_dt.isoformat()}"

                        # 2. OVERDUE
                        elif due_dt and now > (due_dt + cls.OVERDUE_THRESHOLD):
                            if prev_status not in [TaskStatus.OVERDUE.value, TaskStatus.EXPIRED.value]:
                                new_status = TaskStatus.OVERDUE.value
                                event_type = TaskEventType.TASK_OVERDUE.value
                                event_reason = f"Task overdue past due threshold ({due_dt.isoformat()})"

                        # 3. DUE
                        elif due_dt and now >= due_dt:
                            if prev_status in [TaskStatus.PENDING.value, TaskStatus.SCHEDULED.value, "planned"]:
                                new_status = TaskStatus.DUE.value
                                event_type = TaskEventType.TASK_DUE.value
                                event_reason = f"Task reached scheduled due time ({due_dt.isoformat()})"

                        # Apply status transition
                        if new_status != prev_status:
                            update_stmt = (
                                update(FarmTask)
                                .where(FarmTask.id == task.id, FarmTask.status == prev_status)
                                .values(status=new_status, updated_at=utc_now_naive())
                            )
                            update_res = await db.execute(update_stmt)
                            if update_res.rowcount > 0:
                                task.status = new_status
                                task.updated_at = utc_now_naive()
                                stats["tasks_transitioned"] += 1

                                if new_status == TaskStatus.DUE.value:
                                    stats["due"] += 1
                                elif new_status == TaskStatus.OVERDUE.value:
                                    stats["overdue"] += 1
                                elif new_status == TaskStatus.EXPIRED.value:
                                    stats["expired"] += 1

                                if event_type:
                                    event_key = f"task_{event_type.lower().replace('task_', '')}_{task.id}"
                                    await cls._record_task_event(
                                        db=db,
                                        task=task,
                                        event_type=event_type,
                                        event_key=event_key,
                                        scheduled_for=due_dt or exp_dt,
                                        payload={
                                            "task_id": task.id,
                                            "title": task.title,
                                            "previous_status": prev_status,
                                            "new_status": new_status,
                                            "reason": event_reason,
                                            "timestamp": now.isoformat()
                                        }
                                    )

                        # Check proactive reminder eligibility for actionable tasks
                        elif prev_status in [TaskStatus.PENDING.value, TaskStatus.SCHEDULED.value, "planned"]:
                            # Only if legitimate due_at exists (do NOT fabricate dates)
                            if task.due_at and due_dt:
                                reminder_window_start = due_dt - cls.REMINDER_LEAD_TIME
                                if reminder_window_start <= now < due_dt:
                                    reminder_key = f"task_reminder_{task.id}_{int(due_dt.timestamp())}"
                                    created = await cls._record_task_event(
                                        db=db,
                                        task=task,
                                        event_type=TaskEventType.TASK_REMINDER.value,
                                        event_key=reminder_key,
                                        scheduled_for=due_dt,
                                        payload={
                                            "task_id": task.id,
                                            "title": task.title,
                                            "due_at": due_dt.isoformat(),
                                            "lead_hours": 2,
                                            "timestamp": now.isoformat()
                                        }
                                    )
                                    if created:
                                        stats["reminders_created"] += 1

                    except Exception as task_err:
                        logger.error(f"Error processing task {task.id}: {task_err}", exc_info=True)
                        stats["failed"] += 1

                # Commit batch
                await db.commit()

            except Exception as batch_err:
                await db.rollback()
                logger.error(f"Global lifecycle batch failed: {batch_err}", exc_info=True)
                stats["failed"] += 1
                break

        logger.info(
            "TASK_LIFECYCLE_RUN tasks_scanned=%d tasks_transitioned=%d due=%d overdue=%d expired=%d reminders=%d failed=%d",
            stats["tasks_scanned"],
            stats["tasks_transitioned"],
            stats["due"],
            stats["overdue"],
            stats["expired"],
            stats["reminders_created"],
            stats["failed"]
        )

        return stats

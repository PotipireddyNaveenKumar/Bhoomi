import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger("bhoomi.tasks.advisory_lock")

# Deterministic int64 lock identifier for BHOOMI task scheduler
BHOOMI_TASK_SCHEDULER_LOCK_ID = 842011

# In-memory lock fallback for SQLite / non-PostgreSQL testing environments
_sqlite_test_locks: dict[int, asyncio.Lock] = {}


def _is_postgres_session(db: AsyncSession) -> bool:
    try:
        bind = getattr(db, "bind", None)
        if bind and hasattr(bind, "dialect"):
            return "postgres" in bind.dialect.name.lower()
        if hasattr(db, "connection"):
            # Assume postgres if async connection has no sqlite indicator
            bind_str = str(getattr(db, "bind", ""))
            return "sqlite" not in bind_str.lower()
    except Exception:
        pass
    return False


async def try_advisory_lock(db: AsyncSession, lock_id: int = BHOOMI_TASK_SCHEDULER_LOCK_ID) -> bool:
    """
    Attempts to acquire a PostgreSQL distributed advisory lock without blocking.
    Returns True if acquired, False if another process holds the lock.
    Falls back to asyncio.Lock for SQLite/testing.
    """
    if _is_postgres_session(db):
        try:
            res = await db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id})
            acquired = bool(res.scalar())
            if acquired:
                logger.info(f"TASK_SCHEDULER_LOCK_ACQUIRED lock_id={lock_id}")
            else:
                logger.warning(f"TASK_SCHEDULER_LOCK_BUSY lock_id={lock_id} held by another worker")
            return acquired
        except Exception as e:
            logger.error(f"Failed executing pg_try_advisory_lock: {e}")
            # In case of DB error, do not assume lock
            return False
    else:
        # SQLite / in-memory non-postgres fallback
        if lock_id not in _sqlite_test_locks:
            _sqlite_test_locks[lock_id] = asyncio.Lock()
        lock = _sqlite_test_locks[lock_id]
        if lock.locked():
            logger.warning(f"TASK_SCHEDULER_LOCK_BUSY lock_id={lock_id} (in-memory)")
            return False
        await lock.acquire()
        logger.info(f"TASK_SCHEDULER_LOCK_ACQUIRED lock_id={lock_id} (in-memory)")
        return True


async def release_advisory_lock(db: AsyncSession, lock_id: int = BHOOMI_TASK_SCHEDULER_LOCK_ID) -> bool:
    """
    Releases a previously acquired PostgreSQL distributed advisory lock.
    """
    if _is_postgres_session(db):
        try:
            res = await db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
            released = bool(res.scalar())
            logger.info(f"TASK_SCHEDULER_LOCK_RELEASED lock_id={lock_id} released={released}")
            return released
        except Exception as e:
            logger.error(f"Failed executing pg_advisory_unlock: {e}")
            return False
    else:
        lock = _sqlite_test_locks.get(lock_id)
        if lock and lock.locked():
            lock.release()
            logger.info(f"TASK_SCHEDULER_LOCK_RELEASED lock_id={lock_id} (in-memory)")
            return True
        return False


@asynccontextmanager
async def advisory_lock(db: AsyncSession, lock_id: int = BHOOMI_TASK_SCHEDULER_LOCK_ID) -> AsyncGenerator[bool, None]:
    """
    Async context manager for distributed advisory lock.
    Yields True if lock was acquired, False otherwise.
    Releases lock upon context exit if it was acquired.
    """
    acquired = await try_advisory_lock(db, lock_id=lock_id)
    try:
        yield acquired
    finally:
        if acquired:
            await release_advisory_lock(db, lock_id=lock_id)

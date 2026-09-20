import os
import sys
import time
import signal
import asyncio
import logging
import argparse
from datetime import datetime, timezone
from typing import Optional, List

# Ensure repository root is on sys.path when executed directly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.session import AsyncSessionLocal, engine
from app.core.advisory_lock import advisory_lock, BHOOMI_TASK_SCHEDULER_LOCK_ID
from app.services.tasks.lifecycle_service import TaskLifecycleService
from app.models.task_event import TaskSchedulerState
from app.core.datetime_utils import utc_now_naive

# Configure dedicated structured logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("bhoomi.scheduler")


class TaskSchedulerRunner:
    """
    Dedicated background worker process for automatic proactive task lifecycle scheduling.
    Runs periodically (default 15 minutes / 900 seconds).
    Guaranteed single execution across multiple workers via PostgreSQL distributed advisory locking.
    """

    def __init__(self, interval_seconds: int = 900, run_once: bool = False):
        self.interval_seconds = interval_seconds
        self.run_once = run_once
        self._running = True

    def stop(self, signum=None, frame=None):
        logger.info("TASK_SCHEDULER_STOP_REQUESTED received signal, shutting down gracefully...")
        self._running = False

    async def execute_cycle(self) -> dict:
        """
        Executes a single protected global lifecycle cycle and updates durable state.
        """
        cycle_start = time.perf_counter()
        now = datetime.now(timezone.utc)
        start_msg = f"TASK_SCHEDULER_START timestamp={now.isoformat()} interval_seconds={self.interval_seconds}"
        logger.info(start_msg)

        captured_logs: List[str] = [start_msg]

        stats = {
            "success": False,
            "lock_acquired": False,
            "tasks_scanned": 0,
            "tasks_transitioned": 0,
            "due": 0,
            "overdue": 0,
            "expired": 0,
            "reminders_created": 0,
            "failed": 0,
            "duration_ms": 0
        }

        lock_was_acquired = False
        async with AsyncSessionLocal() as session:
            async with advisory_lock(session) as acquired:
                if not acquired:
                    stats["duration_ms"] = int((time.perf_counter() - cycle_start) * 1000)
                    busy_msg = f"TASK_SCHEDULER_LOCK_BUSY another scheduler instance currently holds distributed lock {BHOOMI_TASK_SCHEDULER_LOCK_ID}. Skipping cycle."
                    logger.warning(busy_msg)
                    captured_logs.append(busy_msg)
                    await self._record_state(now, False, stats, captured_logs)
                    return stats

                lock_was_acquired = True
                stats["lock_acquired"] = True
                lock_acq_msg = f"TASK_SCHEDULER_LOCK_ACQUIRED lock_id={BHOOMI_TASK_SCHEDULER_LOCK_ID}"
                logger.info(lock_acq_msg)
                captured_logs.append(lock_acq_msg)

                try:
                    res = await TaskLifecycleService.run_global_lifecycle(db=session, reference_now=now)
                    stats.update(res)
                    stats["success"] = True

                    lifecycle_msg = (
                        f"TASK_LIFECYCLE_RUN tasks_scanned={stats['tasks_scanned']} "
                        f"tasks_transitioned={stats['tasks_transitioned']} due={stats['due']} "
                        f"overdue={stats['overdue']} expired={stats['expired']} "
                        f"reminders={stats['reminders_created']} failed={stats['failed']}"
                    )
                    captured_logs.append(lifecycle_msg)
                except Exception as e:
                    stats["failed"] += 1
                    err_msg = f"TASK_SCHEDULER_ERROR cycle execution failed: {e}"
                    logger.error(err_msg, exc_info=True)
                    captured_logs.append(err_msg)
                finally:
                    stats["duration_ms"] = int((time.perf_counter() - cycle_start) * 1000)
                    result_msg = (
                        f"TASK_SCHEDULER_RESULT success={stats['success']} duration_ms={stats['duration_ms']} "
                        f"tasks_scanned={stats['tasks_scanned']} tasks_transitioned={stats['tasks_transitioned']} "
                        f"due={stats['due']} overdue={stats['overdue']} expired={stats['expired']} "
                        f"reminders={stats['reminders_created']} failed={stats['failed']}"
                    )
                    logger.info(result_msg)
                    captured_logs.append(result_msg)

                    rel_msg = f"TASK_SCHEDULER_LOCK_RELEASED lock_id={BHOOMI_TASK_SCHEDULER_LOCK_ID} released=true"
                    logger.info(rel_msg)
                    captured_logs.append(rel_msg)

        # Persist state & execution logs to database in an isolated session
        await self._record_state(now, lock_was_acquired, stats, captured_logs)
        return stats

    async def _record_state(
        self,
        now: datetime,
        acquired: bool,
        stats: dict,
        logs: List[str]
    ):
        """Persists heartbeat & execution state to task_scheduler_state table in isolated session."""
        try:
            async with AsyncSessionLocal() as state_session:
                state = await state_session.get(TaskSchedulerState, "global_scheduler")
                if not state:
                    state = TaskSchedulerState(id="global_scheduler")
                    state_session.add(state)
                state.last_run_at = now
                state.consecutive_ticks = (state.consecutive_ticks or 0) + 1
                state.interval_seconds = self.interval_seconds
                state.process_pid = os.getpid()
                state.last_lock_acquired = acquired
                state.last_run_stats = stats
                state.last_run_logs = logs
                state.updated_at = utc_now_naive()
                await state_session.commit()
        except Exception as state_err:
            logger.error(f"Could not persist TaskSchedulerState: {state_err}", exc_info=True)

    async def run(self):
        """
        Main loop of the dedicated scheduler process.
        """
        logger.info(
            "TASK_SCHEDULER_INIT interval_seconds=%d run_once=%s",
            self.interval_seconds,
            self.run_once
        )

        # Wait 2 seconds for app boot and DB initialization before first cycle
        try:
            await asyncio.sleep(2)
            await self.execute_cycle()
        except Exception as e:
            logger.error(f"TASK_SCHEDULER_STARTUP_CYCLE_ERROR: {e}", exc_info=True)

        if self.run_once:
            logger.info("TASK_SCHEDULER_EXIT run_once completed.")
            return

        while self._running:
            try:
                for _ in range(self.interval_seconds):
                    if not self._running:
                        break
                    await asyncio.sleep(1)

                if self._running:
                    await self.execute_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"TASK_SCHEDULER_UNEXPECTED_ERROR in loop: {e}", exc_info=True)
                await asyncio.sleep(5)

        logger.info("TASK_SCHEDULER_SHUTDOWN completed cleanly.")


def main():
    from app.core.config import settings

    parser = argparse.ArgumentParser(description="BHOOMI Proactive Task Lifecycle Scheduler")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Cadence interval in seconds (default from settings)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Run a single cycle and exit"
    )
    args = parser.parse_args()

    interval = args.interval if args.interval is not None else settings.TASK_SCHEDULER_INTERVAL_SECONDS
    runner = TaskSchedulerRunner(interval_seconds=interval, run_once=args.once)

    # Register OS signals for graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        signal.signal(signal.SIGINT, runner.stop)
        signal.signal(signal.SIGTERM, runner.stop)
    except Exception:
        pass

    try:
        loop.run_until_complete(runner.run())
    finally:
        loop.run_until_complete(engine.dispose())
        loop.close()


if __name__ == "__main__":
    main()

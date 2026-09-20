import os
import sys
import time
import signal
import asyncio
import logging
import argparse
from datetime import datetime, timezone
from typing import Optional

# Ensure repository root is on sys.path when executed directly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.session import AsyncSessionLocal, engine
from app.core.advisory_lock import advisory_lock
from app.services.tasks.lifecycle_service import TaskLifecycleService

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
        Executes a single protected global lifecycle cycle.
        """
        cycle_start = time.perf_counter()
        now = datetime.now(timezone.utc)
        logger.info(
            "TASK_SCHEDULER_START timestamp=%s interval_seconds=%d",
            now.isoformat(),
            self.interval_seconds
        )

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

        async with AsyncSessionLocal() as session:
            async with advisory_lock(session) as acquired:
                if not acquired:
                    stats["duration_ms"] = int((time.perf_counter() - cycle_start) * 1000)
                    logger.warning(
                        "TASK_SCHEDULER_LOCK_BUSY another scheduler instance currently holds the distributed lock. Skipping cycle."
                    )
                    return stats

                stats["lock_acquired"] = True
                try:
                    res = await TaskLifecycleService.run_global_lifecycle(db=session, reference_now=now)
                    stats.update(res)
                    stats["success"] = True
                except Exception as e:
                    stats["failed"] += 1
                    logger.error(f"TASK_SCHEDULER_ERROR cycle execution failed: {e}", exc_info=True)
                finally:
                    stats["duration_ms"] = int((time.perf_counter() - cycle_start) * 1000)
                    logger.info(
                        "TASK_SCHEDULER_RESULT success=%s duration_ms=%d tasks_scanned=%d tasks_transitioned=%d due=%d overdue=%d expired=%d reminders=%d failed=%d",
                        stats["success"],
                        stats["duration_ms"],
                        stats["tasks_scanned"],
                        stats["tasks_transitioned"],
                        stats["due"],
                        stats["overdue"],
                        stats["expired"],
                        stats["reminders_created"],
                        stats["failed"]
                    )

        return stats

    async def run(self):
        """
        Main loop of the dedicated scheduler process.
        """
        logger.info(
            "TASK_SCHEDULER_INIT interval_seconds=%d run_once=%s",
            self.interval_seconds,
            self.run_once
        )

        # Initial run on startup
        await self.execute_cycle()

        if self.run_once:
            logger.info("TASK_SCHEDULER_EXIT run_once completed.")
            return

        while self._running:
            try:
                # Sleep in short increments to allow responsive shutdown
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
                await asyncio.sleep(10)

        logger.info("TASK_SCHEDULER_SHUTDOWN completed cleanly.")


def main():
    parser = argparse.ArgumentParser(description="BHOOMI Proactive Task Lifecycle Scheduler")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("TASK_SCHEDULER_INTERVAL_SECONDS", "900")),
        help="Cadence interval in seconds (default: 900 / 15 minutes)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Run a single cycle and exit"
    )
    args = parser.parse_args()

    runner = TaskSchedulerRunner(interval_seconds=args.interval, run_once=args.once)

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

#!/bin/bash
set -e

echo "Starting BHOOMI background task scheduler worker..."
python -m app.services.tasks.scheduler_runner --interval "${TASK_SCHEDULER_INTERVAL_SECONDS:-900}" &
SCHEDULER_PID=$!

echo "Starting BHOOMI FastAPI web application on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

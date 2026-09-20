#!/bin/bash
set -e

echo "Applying BHOOMI database migrations..."
python -m alembic upgrade head || true

echo "Starting BHOOMI background task scheduler worker..."
python -u -m app.services.tasks.scheduler_runner &
SCHEDULER_PID=$!
echo "BHOOMI background scheduler worker started with PID $SCHEDULER_PID"

echo "Starting BHOOMI FastAPI web application on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"


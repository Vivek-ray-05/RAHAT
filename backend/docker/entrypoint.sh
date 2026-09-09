#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting server..."
if [ "$UVICORN_RELOAD" = "true" ]; then
    # Local dev only (docker-compose.yml sets this) -- file-watching and
    # auto-restart on every source change, at the cost of the reloader's
    # extra memory/CPU overhead.
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    # Production: no reload, and defaults to a single worker on purpose.
    # More than one worker means more than one process, each with its own
    # in-memory per-run engine caches (RiskEngine/MobilityEngine/
    # DecisionGovernor -- see simulation_service.py) and no sticky routing
    # between them within a single container, so raising UVICORN_WORKERS
    # here has the same caveat documented for the multi-replica case:
    # tick-advancement for one run must consistently land on the same
    # worker or its soil-saturation/replan-cooldown state resets.
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"
fi

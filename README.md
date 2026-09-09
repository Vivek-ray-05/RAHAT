# RAHAT

A human-in-the-loop disaster evacuation decision-support platform for cities.

**Core principle:** AI recommends. Humans approve. Every decision is explainable, auditable, and reversible.

Risk, vulnerability, and route-planning engines generate evacuation recommendations from live or simulated city data. A Zone Admin reviews and approves, modifies, or rejects every recommendation before it takes effect — nothing is auto-executed.

## Status

Core loop working end-to-end: real Bengaluru zone/road/shelter data, simulated flood scenarios, risk/vulnerability scoring, evacuation recommendations, the full human approval workflow, real-time updates, and CI. See `backend/app/` for the FastAPI backend.

## Stack

- **Backend:** FastAPI, SQLModel, PostgreSQL, Alembic, Redis, WebSockets, NetworkX
- **Frontend:** React, Vite, Tailwind, Leaflet
- **Infra:** Docker Compose (local), Railway (deploy)

## Local setup

```bash
cp .env.example backend/.env   # fill in JWT_SECRET at minimum
docker compose up --build
```

Backend: http://localhost:8000
Frontend: http://localhost:5173

## Deployment

Deploys as three Railway services in one project — the backend and frontend each build from this repo's Dockerfiles, Postgres and Redis are Railway's managed plugins.

### 1. Create the project and databases

1. New Railway project → **Add Postgres** and **Add Redis** from Railway's plugin catalog (don't use the `postgres`/`redis` services from `docker-compose.yml` for this — that compose file is for local dev only).

### 2. Backend service

1. **New Service → Deploy from GitHub repo**, pick this repo.
2. **Settings → Root Directory**: `backend`. Railway will find `backend/railway.toml`, which points it at `docker/Dockerfile`.
3. **Variables** tab, add:
   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference the Postgres plugin) |
   | `REDIS_URL` | `${{Redis.REDIS_URL}}` (reference the Redis plugin) |
   | `JWT_SECRET` | output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` — generate your own, don't reuse the repo's placeholder |
   | `DEV_MODE` | `false` |
   | `CORS_ORIGINS` | your frontend's Railway URL once you have it (step 3) — comma-separated if more than one, no wildcard |
   | `BREVO_API_KEY`, `BREVO_FROM_EMAIL` | optional, leave unset if you don't need real emails yet — notifications fail safely with a clear "not configured" status either way |
4. Deploy. Migrations run automatically on every start (`backend/docker/entrypoint.sh`) — you don't need a separate migration step.
5. Railway gives the service a public URL (or generate one under **Settings → Networking**) — that's your `VITE_API_BASE_URL` for the next step, and its `wss://` equivalent is `VITE_WS_URL`.

### 3. Frontend service

1. **New Service → Deploy from GitHub repo**, same repo again.
2. **Settings → Root Directory**: `frontend`. Railway will find `frontend/railway.toml`, which points it at `Dockerfile.prod` (a real `vite build` served by nginx — not the dev server `docker-compose.yml` uses locally).
3. **Variables** tab — these must be **build-time** variables (Railway: mark them under the build/deploy variables that apply at build, not just runtime), since Vite bakes `import.meta.env.VITE_*` into the JS at build time, not read live:
   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | the backend's public URL from step 2.5, e.g. `https://rahat-backend.up.railway.app` |
   | `VITE_WS_URL` | same host, `wss://` scheme, e.g. `wss://rahat-backend.up.railway.app` |
4. Deploy. Generate a public domain under **Settings → Networking**.
5. Go back to the **backend** service and set `CORS_ORIGINS` to this frontend URL, then redeploy the backend (CORS is checked at request time, so this has to point at the real frontend origin or every request from it gets rejected).

### 4. Seed demo data (optional)

The `backend/scripts/seed_demo_city.py` / `seed_demo_users.py` scripts that built the local dev dataset need a one-off run against the deployed database — either run them locally with `DATABASE_URL` temporarily pointed at Railway's Postgres (copy the value from the Variables tab), or open a Railway shell on the backend service and run them there.

### Notes

- The `backend2` service in `docker-compose.yml` is a **local-only** artifact proving Redis-backed state (OTP, rate limiting, WS pub/sub) is genuinely shared across processes — it doesn't need an equivalent on Railway. If you ever want more than one backend instance there, use Railway's own replica/scaling settings; the Redis-backed state is exactly what makes that safe now.
- `UVICORN_WORKERS` defaults to 1 in production (`backend/docker/entrypoint.sh`) on purpose — see that file's comment on why raising it needs the same care as adding replicas.
- Frontend `VITE_*` variables are baked in at build time. Changing `VITE_API_BASE_URL` later means rebuilding the frontend service, not just restarting it.

## Architecture

```
Frontend (React/WS)
      |
FastAPI Gateway
      |
Application Services (Simulation, Recommendation, Approval, Notification, Audit)
      |
Domain Engines (Risk, Vulnerability, Mobility, Shelter Allocation, Decision Governor)
      |
PostgreSQL
```

Every AI recommendation moves through: `pending_review → approved / modified / rejected → executed / expired`, with a full audit trail.

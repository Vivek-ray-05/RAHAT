# RAHAT

[![CI](https://github.com/Vivek-ray-05/RAHAT/actions/workflows/ci.yml/badge.svg)](https://github.com/Vivek-ray-05/RAHAT/actions/workflows/ci.yml)
[![Live on Railway](https://img.shields.io/badge/demo-live-brightgreen)](https://rahat-frontend-production.up.railway.app)

A human-in-the-loop disaster evacuation decision-support platform for cities, built end to end on real Bengaluru data.

**Core principle:** AI recommends. Humans approve. Every decision is explainable, auditable, and reversible.

Deterministic risk, vulnerability, and route-planning engines score every zone from live or simulated city data and produce a ranked evacuation plan. Nothing is auto-executed — a Zone Admin reviews, approves, modifies, or rejects every recommendation before it takes effect, and every transition writes a permanent audit record.

## Try it live

**https://rahat-frontend-production.up.railway.app**

| Role | Email | Password |
|---|---|---|
| Central Coordinator | `coordinator@rahat.dev` | `demo1234` |
| Zone Admin (Marathahalli) | `za.marathahalli@rahat.dev` | `demo1234` |
| Zone Admin (Bellandur) | `za.bellandur@rahat.dev` | `demo1234` |
| Zone Admin (HSR Layout) | `za.hsrlayout@rahat.dev` | `demo1234` |
| NDRF | `ndrf.bellandur@rahat.dev` | `demo1234` |
| Citizen | any phone number, OTP `1234` | — |

Log in as Coordinator to see the city overview; as a Zone Admin to review and act on pending recommendations; as NDRF to see an assigned evacuation route; as a Citizen to browse shelters and file an incident report.

## What makes this real, not a mockup

- **28 real Bengaluru localities** — real building-density-derived population, real SRTM elevation, real hospital counts and named shelter candidates, all pulled live from OpenStreetMap and opentopodata.org, not hand-typed.
- **A real 112-edge road network** computed with OSMnx + A* over the actual Bengaluru drivable graph, not a hand-picked handful of roads.
- **A flood-risk model checked against real flood history** — ranking zones by real elevation correctly placed 10 of 12 documented 2022–2024 Bengaluru flood zones into the more-flood-prone half. The model's one known limitation: it can't see lake-encroachment or drainage-driven flooding (e.g. JP Nagar, Electronic City) since that's not captured by elevation alone.
- **A real approval workflow, not a toggle** — approve, modify (reassign shelter/population), or reject; every action writes an `AuditEvent` with the real actor, before-state, and after-state.
- **Real-time, and actually cross-process** — the live tick stream runs on Redis pub/sub, not polling, verified by pushing a tick from one backend container and receiving it on a WebSocket connected to a *different* one.
- **A real security pass** — a full audit found and fixed cross-zone authorization gaps, an unauthenticated endpoint, and a shelter-capacity overflow bug, each reproduced live against the running app before being fixed, not just reasoned about.
- **91+ backend tests** (unit engines + integration against a real transaction-isolated Postgres), running in CI on every push alongside a Bandit security scan, `pip-audit`, `npm audit`, and a full `docker compose` smoke test.

## Stack

| | |
|---|---|
| **Backend** | FastAPI, SQLModel, PostgreSQL, Alembic, Redis, WebSockets, NetworkX |
| **Frontend** | React, Vite, Tailwind, Leaflet |
| **Infra** | Docker Compose (local), Railway (deployed), GitHub Actions (CI) |

## Architecture

```
Frontend (React/WS)
      |
FastAPI Gateway  --  rate-limited, JWT-authenticated
      |
Application Services (Simulation, Recommendation, Approval, Notification, Audit)
      |
Domain Engines (Risk, Vulnerability, Mobility, Shelter Allocation, Decision Governor)
      |
PostgreSQL  +  Redis (OTP store, rate limiter, tick-stream pub/sub)
```

Every AI recommendation moves through `pending_review -> approved / modified / rejected -> executed / expired`, with a full audit trail at each step.

## Local setup

```bash
cp .env.example backend/.env   # fill in JWT_SECRET at minimum
docker compose up --build
```

Backend: http://localhost:8000
Frontend: http://localhost:5173

Run the backend test suite:

```bash
cd backend && python -m pytest tests/ -v
```

## Deployment

The live instance above runs on Railway: one project, three services (backend, frontend, plus Postgres and Redis as managed plugins). Two ways to get there:

**Railway CLI** (what was actually used for the live deployment) — install `@railway/cli`, `railway login`, then `railway up <dir> --path-as-root --service <name>` for each of `backend/` and `frontend/`. A few CLI-specific gotchas (it ignores `railway.toml`'s builder config and needs `RAILWAY_DOCKERFILE_PATH` set explicitly instead, Railway's `DATABASE_URL` needs a driver-suffix fix for SQLAlchemy, seeding the deployed DB needs `railway ssh` rather than exposing Postgres publicly) are worth knowing before repeating this — ask if you're doing it again.

**Railway dashboard** (GitHub-integrated, auto-deploys on push) — the more conventional path if you connect this repo through Railway's GitHub App:

<details>
<summary>Full dashboard walkthrough</summary>

### 1. Create the project and databases

New Railway project -> **Add Postgres** and **Add Redis** from Railway's plugin catalog (don't use the `postgres`/`redis` services from `docker-compose.yml` for this — that compose file is for local dev only).

### 2. Backend service

1. **New Service -> Deploy from GitHub repo**, pick this repo.
2. **Settings -> Root Directory**: `backend`. Railway will find `backend/railway.toml`, which points it at `docker/Dockerfile`.
3. **Variables** tab, add:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference the Postgres plugin) |
   | `REDIS_URL` | `${{Redis.REDIS_URL}}` (reference the Redis plugin) |
   | `JWT_SECRET` | output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` — generate your own, don't reuse the repo's placeholder |
   | `DEV_MODE` | `false` |
   | `CORS_ORIGINS` | your frontend's Railway URL once you have it (step 3) — comma-separated if more than one, no wildcard |
   | `BREVO_API_KEY`, `BREVO_FROM_EMAIL` | optional, leave unset if you don't need real emails yet — notifications fail safely with a clear "not configured" status either way |
4. Deploy. Migrations run automatically on every start (`backend/docker/entrypoint.sh`) — no separate migration step needed.
5. Railway gives the service a public URL (or generate one under **Settings -> Networking**) — that's your `VITE_API_BASE_URL` for the next step, and its `wss://` equivalent is `VITE_WS_URL`.

### 3. Frontend service

1. **New Service -> Deploy from GitHub repo**, same repo again.
2. **Settings -> Root Directory**: `frontend`. Railway will find `frontend/railway.toml`, which points it at `Dockerfile.prod` (a real `vite build` served by nginx — not the dev server `docker-compose.yml` uses locally).
3. **Variables** tab — these must be **build-time** variables, since Vite bakes `import.meta.env.VITE_*` into the JS at build time, not read live:

   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | the backend's public URL from step 2.5 |
   | `VITE_WS_URL` | same host, `wss://` scheme |
4. Deploy. Generate a public domain under **Settings -> Networking**.
5. Go back to the **backend** service and set `CORS_ORIGINS` to this frontend URL, then redeploy the backend.

### 4. Seed demo data (optional)

`backend/scripts/seed_demo_city.py` / `seed_demo_users.py` need a one-off run against the deployed database — either run them locally with `DATABASE_URL` temporarily pointed at Railway's Postgres, or use `railway ssh` on the backend service.

</details>

**Worth knowing either way:**
- `docker-compose.yml`'s `backend2` service is a **local-only** artifact proving Redis-backed state (OTP, rate limiting, WS pub/sub) is genuinely shared across processes — it has no Railway equivalent needed. Scale via Railway's own replica settings if you ever want more than one instance; the Redis-backed state is exactly what makes that safe.
- `UVICORN_WORKERS` defaults to 1 in production on purpose (`backend/docker/entrypoint.sh`) — raising it needs the same care as adding replicas, see that file's comment.
- Frontend `VITE_*` variables are baked in at build time. Changing `VITE_API_BASE_URL` later means rebuilding the frontend service, not just restarting it.


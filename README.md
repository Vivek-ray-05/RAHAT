# RAHAT

A human-in-the-loop disaster evacuation decision-support platform for cities.

**Core principle:** AI recommends. Humans approve. Every decision is explainable, auditable, and reversible.

Risk, vulnerability, and route-planning engines generate evacuation recommendations from live or simulated city data. A Zone Admin reviews and approves, modifies, or rejects every recommendation before it takes effect — nothing is auto-executed.

## Status

Early build. See `backend/app/` for the in-progress FastAPI + PostgreSQL backend.

## Stack

- **Backend:** FastAPI, SQLModel, PostgreSQL, Alembic, WebSockets, NetworkX
- **Frontend:** React, Vite, Tailwind, Leaflet
- **Infra:** Docker Compose

## Local setup

```bash
cp .env.example backend/.env   # fill in JWT_SECRET at minimum
docker compose up --build
```

Backend: http://localhost:8000
Frontend: http://localhost:5173

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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import auth, simulation, recommendations, approvals, zones, shelters, citizen_reports, roads

app = FastAPI(title="RAHAT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(simulation.router)
app.include_router(recommendations.router)
app.include_router(approvals.router)
app.include_router(zones.router)
app.include_router(shelters.router)
app.include_router(citizen_reports.router)
app.include_router(roads.router)


@app.get("/health")
def health():
    return {"status": "ok"}

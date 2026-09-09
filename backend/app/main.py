from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.core.body_size_limit import BodySizeLimitMiddleware
from app.core.rate_limit import limiter
from app.api.routes import auth, simulation, recommendations, approvals, zones, shelters, citizen_reports, roads

app = FastAPI(title="RAHAT API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(BodySizeLimitMiddleware)

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

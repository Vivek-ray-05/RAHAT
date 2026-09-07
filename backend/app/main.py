from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import auth, simulation

from app.api.routes import auth, simulation, recommendations, approvals

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


app.include_router(auth.router)
app.include_router(simulation.router)
app.include_router(recommendations.router)
app.include_router(approvals.router)

@app.get("/health")
def health():
    return {"status": "ok"}
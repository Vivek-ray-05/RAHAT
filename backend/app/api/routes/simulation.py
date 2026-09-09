import asyncio

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.roles import RoleEnum
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.simulation import SimulationRun
from app.models.user import User
from app.schemas.simulation import SimulationRunResponse, StartSimulationRequest, TickResponse
from app.services import simulation_service as svc

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _get_run_or_404(session: Session, run_id: int) -> SimulationRun:
    run = session.get(SimulationRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation run not found")
    return run


@router.post("/start", response_model=SimulationRunResponse)
def start(
    payload: StartSimulationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    try:
        run = svc.start_simulation(session, payload.scenario_id, current_user.id)
    except svc.SimulationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return run


@router.post("/{run_id}/tick", response_model=TickResponse)
def advance(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    run = _get_run_or_404(session, run_id)
    try:
        tick = svc.advance_tick(session, run)
    except svc.SimulationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return tick


@router.get("/{run_id}/latest-tick", response_model=TickResponse)
def latest_tick(run_id: int, session: Session = Depends(get_session)):
    tick = svc.get_latest_tick(session, run_id)
    if tick is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No ticks yet for this run")
    return tick


@router.post("/{run_id}/pause", response_model=SimulationRunResponse)
def pause(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    run = _get_run_or_404(session, run_id)
    return svc.pause_simulation(session, run)


@router.post("/{run_id}/resume", response_model=SimulationRunResponse)
def resume(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    run = _get_run_or_404(session, run_id)
    return svc.resume_simulation(session, run)


@router.post("/{run_id}/complete", response_model=SimulationRunResponse)
def complete(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    run = _get_run_or_404(session, run_id)
    return svc.complete_simulation(session, run)


@router.websocket("/{run_id}/ws")
async def tick_stream(websocket: WebSocket, run_id: int, token: str, session: Session = Depends(get_session)):
    """Tick-streaming WS, gated by a JWT passed as ?token=. Pushes a
    new payload whenever the latest tick number changes."""
    try:
        payload = decode_access_token(token)
        user = session.get(User, int(payload.get("sub")))
    except JWTError:
        user = None

    if user is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    last_sent_tick_number: int | None = None
    try:
        while True:
            tick = svc.get_latest_tick(session, run_id)
            if tick is not None and tick.tick_number != last_sent_tick_number:
                await websocket.send_json({
                    "id": tick.id,
                    "tick_number": tick.tick_number,
                    "timestamp": tick.timestamp.isoformat(),
                    "raw_state_json": tick.raw_state_json,
                })
                last_sent_tick_number = tick.tick_number
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

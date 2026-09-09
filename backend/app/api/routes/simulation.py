import asyncio
import contextlib
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlmodel import Session

from app.api.deps import get_current_user, require_role
from app.core.redis_client import async_redis_client
from app.core.roles import RoleEnum
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.simulation import SimulationRun
from app.models.user import User
from app.schemas.simulation import SimulationRunResponse, StartSimulationRequest, TickResponse
from app.services import simulation_service as svc

router = APIRouter(prefix="/simulation", tags=["simulation"])

_coordinator_only = require_role(RoleEnum.CENTRAL_COORDINATOR)


def _get_run_or_404(session: Session, run_id: int) -> SimulationRun:
    run = session.get(SimulationRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation run not found")
    return run


@router.post("/start", response_model=SimulationRunResponse)
def start(
    payload: StartSimulationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(_coordinator_only),
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
    current_user: User = Depends(_coordinator_only),
):
    run = _get_run_or_404(session, run_id)
    try:
        tick = svc.advance_tick(session, run)
    except svc.SimulationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return tick


@router.get("/{run_id}/latest-tick", response_model=TickResponse)
def latest_tick(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tick = svc.get_latest_tick(session, run_id)
    if tick is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No ticks yet for this run")
    return tick


@router.post("/{run_id}/pause", response_model=SimulationRunResponse)
def pause(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(_coordinator_only),
):
    run = _get_run_or_404(session, run_id)
    return svc.pause_simulation(session, run)


@router.post("/{run_id}/resume", response_model=SimulationRunResponse)
def resume(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(_coordinator_only),
):
    run = _get_run_or_404(session, run_id)
    return svc.resume_simulation(session, run)


@router.post("/{run_id}/complete", response_model=SimulationRunResponse)
def complete(
    run_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(_coordinator_only),
):
    run = _get_run_or_404(session, run_id)
    return svc.complete_simulation(session, run)


async def _forward_ticks(pubsub, websocket: WebSocket, last_sent: list[int | None]) -> None:
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        data = json.loads(message["data"])
        if data["tick_number"] != last_sent[0]:
            await websocket.send_json(data)
            last_sent[0] = data["tick_number"]


async def _wait_for_client_disconnect(websocket: WebSocket) -> None:
    """pubsub.listen() only tells us about new Redis messages -- it has
    no idea if the client is still there. Without this running
    alongside it, a client that goes away leaves the handler blocked
    forever waiting on Redis, which in turn blocks the server from
    ever shutting down cleanly (found by an actual reload hanging
    under load-test traffic, not by inspection)."""
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return


@router.websocket("/{run_id}/ws")
async def tick_stream(websocket: WebSocket, run_id: int, token: str, session: Session = Depends(get_session)):
    """Tick-streaming WS, gated by a JWT passed as ?token=. Pushed via
    Redis pub/sub the moment a tick is advanced -- works even if the
    request that advanced it landed on a different backend process
    than this WS connection (see simulation_service.tick_channel)."""
    try:
        payload = decode_access_token(token)
        user = session.get(User, int(payload.get("sub")))
    except JWTError:
        user = None

    if user is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    last_sent_tick_number: list[int | None] = [None]

    pubsub = async_redis_client.pubsub()
    await pubsub.subscribe(svc.tick_channel(run_id))
    try:
        # Catch up first: a tick may already exist from before this
        # connection subscribed, and pub/sub only delivers messages
        # published after subscribe() -- it wouldn't replay that one.
        latest = svc.get_latest_tick(session, run_id)
        if latest is not None:
            await websocket.send_json({
                "id": latest.id,
                "tick_number": latest.tick_number,
                "timestamp": latest.timestamp.isoformat(),
                "raw_state_json": latest.raw_state_json,
            })
            last_sent_tick_number[0] = latest.tick_number

        forward_task = asyncio.create_task(_forward_ticks(pubsub, websocket, last_sent_tick_number))
        disconnect_task = asyncio.create_task(_wait_for_client_disconnect(websocket))
        try:
            done, pending = await asyncio.wait(
                [forward_task, disconnect_task], return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            for task in done:
                if task.exception() and not isinstance(task.exception(), WebSocketDisconnect):
                    raise task.exception()
        except WebSocketDisconnect:
            pass
    finally:
        await pubsub.unsubscribe(svc.tick_channel(run_id))
        await pubsub.aclose()

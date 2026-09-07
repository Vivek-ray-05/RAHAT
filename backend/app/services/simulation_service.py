"""
Owns a SimulationRun's lifecycle: start it, advance it tick by tick,
pause/complete it. Each tick pulls readings from an ingestion adapter
(synthetic for now) and persists a SimulationTick snapshot.

This replaces the old prototype's single global in-memory simulation
loop -- state lives in Postgres, so a restart doesn't lose it, and
nothing here auto-executes an evacuation decision. Decision-engine
wiring (risk/vulnerability/mobility/governor) happens on top of this
in Phase 3; this file's job is just: manage the run, produce ticks.
"""
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.enums import SimulationStatus
from app.ingestion.synthetic_adapter import SyntheticFloodAdapter
from app.models.scenario import Scenario
from app.models.simulation import SimulationRun, SimulationTick
from app.models.zone import Zone


class SimulationError(Exception):
    pass


def start_simulation(session: Session, scenario_id: int, started_by_user_id: int) -> SimulationRun:
    scenario = session.get(Scenario, scenario_id)
    if scenario is None:
        raise SimulationError(f"No scenario with id {scenario_id}")

    run = SimulationRun(
        scenario_id=scenario_id,
        started_by_user_id=started_by_user_id,
        status=SimulationStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_latest_tick(session: Session, simulation_run_id: int) -> SimulationTick | None:
    return session.exec(
        select(SimulationTick)
        .where(SimulationTick.simulation_run_id == simulation_run_id)
        .order_by(SimulationTick.tick_number.desc())
    ).first()


def advance_tick(session: Session, run: SimulationRun) -> SimulationTick:
    if run.status != SimulationStatus.RUNNING:
        raise SimulationError(f"Cannot advance a {run.status.value} simulation")

    scenario = session.get(Scenario, run.scenario_id)
    severity = scenario.config_json.get("severity", 1.0)

    latest = get_latest_tick(session, run.id)
    next_tick_number = 0 if latest is None else latest.tick_number + 1

    zone_ids = [z.id for z in session.exec(select(Zone)).all()]
    if not zone_ids:
        raise SimulationError("No zones exist to simulate -- seed the city first")

    adapter = SyntheticFloodAdapter(
        zone_ids=zone_ids, tick=next_tick_number, severity=severity,
        simulation_run_id=run.id,
    )
    readings = adapter.ingest_batch(session)

    raw_state = {
        "tick": next_tick_number,
        "scenario_type": scenario.scenario_type,
        "readings": [
            {"zone_id": r.zone_id, "event_type": r.event_type, "value": r.value}
            for r in readings
        ],
    }

    tick = SimulationTick(
        simulation_run_id=run.id,
        tick_number=next_tick_number,
        timestamp=datetime.now(timezone.utc),
        raw_state_json=raw_state,
    )
    session.add(tick)
    session.commit()
    session.refresh(tick)
    return tick


def pause_simulation(session: Session, run: SimulationRun) -> SimulationRun:
    run.status = SimulationStatus.PAUSED
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def resume_simulation(session: Session, run: SimulationRun) -> SimulationRun:
    run.status = SimulationStatus.RUNNING
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def complete_simulation(session: Session, run: SimulationRun) -> SimulationRun:
    run.status = SimulationStatus.COMPLETED
    run.ended_at = datetime.now(timezone.utc)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run

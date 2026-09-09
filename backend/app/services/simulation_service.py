"""
Owns a SimulationRun's lifecycle: start it, advance it tick by tick,
pause/complete it. Each tick pulls readings from an ingestion adapter
(synthetic for now), scores every zone's risk and vulnerability, finds
each zone's route to its nearest shelter, and persists all of it --
this is the real state, in Postgres, not an in-memory dict that
vanishes on restart.

If a tick's conditions warrant it, a replan is triggered and turned
into pending recommendations -- nothing is executed automatically,
that only happens once a zone admin approves.
"""
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.enums import SimulationStatus
from app.engines.governor.decision_governor import DecisionGovernor, ShelterState, ZoneState
from app.engines.mobility.mobility_agent import MobilityEngine
from app.engines.risk.risk_agent import RiskEngine
from app.engines.vulnerability.vulnerability_agent import score_zone as score_vulnerability
from app.ingestion.synthetic_adapter import SyntheticFloodAdapter
from app.models.risk_score import RiskScore
from app.models.road import Road
from app.models.route_option import RouteOption
from app.models.scenario import Scenario
from app.models.shelter import Shelter
from app.models.simulation import SimulationRun, SimulationTick
from app.models.vulnerability_score import VulnerabilityScore
from app.models.zone import Zone
from app.services import recommendation_service, trigger_evaluator


class SimulationError(Exception):
    pass


# One RiskEngine/MobilityEngine/DecisionGovernor per active run, so
# stateful bits (soil saturation history, the routing graph, replan
# cooldown) persist correctly across ticks. Process-local -- fine for
# a single backend worker; a multi-worker deployment would need this
# moved to something shared (Phase 6 concern, not relevant yet).
_risk_engines: dict[int, RiskEngine] = {}
_mobility_engines: dict[int, MobilityEngine] = {}
_governors: dict[int, DecisionGovernor] = {}


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


def _get_risk_engine(run_id: int) -> RiskEngine:
    if run_id not in _risk_engines:
        _risk_engines[run_id] = RiskEngine()
    return _risk_engines[run_id]


def _get_mobility_engine(run_id: int, zones: list[Zone], roads: list[Road], shelters: list[Shelter]) -> MobilityEngine:
    if run_id not in _mobility_engines:
        _mobility_engines[run_id] = MobilityEngine(zones, roads, shelters)
    return _mobility_engines[run_id]


def _get_governor(run_id: int) -> DecisionGovernor:
    if run_id not in _governors:
        _governors[run_id] = DecisionGovernor()
    return _governors[run_id]


def get_active_mobility_engine(run_id: int) -> MobilityEngine | None:
    """The live routing graph for a run that has already ticked at
    least once, if one exists -- used to apply a road block immediately
    instead of waiting for the next tick to rebuild it."""
    return _mobility_engines.get(run_id)


def advance_tick(session: Session, run: SimulationRun) -> SimulationTick:
    if run.status != SimulationStatus.RUNNING:
        raise SimulationError(f"Cannot advance a {run.status.value} simulation")

    scenario = session.get(Scenario, run.scenario_id)
    severity = scenario.config_json.get("severity", 1.0)

    latest = get_latest_tick(session, run.id)
    next_tick_number = 0 if latest is None else latest.tick_number + 1

    zones = session.exec(select(Zone)).all()
    roads = session.exec(select(Road)).all()
    shelters = session.exec(select(Shelter)).all()
    if not zones:
        raise SimulationError("No zones exist to simulate -- seed the city first")

    # 0. Expire any recommendation from an earlier tick that a zone
    # admin never acted on before its TTL ran out
    recommendation_service.expire_stale(session, simulation_run_id=run.id)

    # 1. Synthetic sensor readings for this tick
    adapter = SyntheticFloodAdapter(
        zone_ids=[z.id for z in zones], tick=next_tick_number, severity=severity,
        simulation_run_id=run.id,
    )
    readings = adapter.ingest_batch(session)
    readings_by_zone: dict[int, dict[str, float]] = {}
    for r in readings:
        readings_by_zone.setdefault(r.zone_id, {})[r.event_type] = r.value

    # 2. Risk + vulnerability scoring per zone (pure computation, no
    # DB rows yet -- those need a tick id, which doesn't exist until
    # step 4)
    risk_engine = _get_risk_engine(run.id)
    risk_by_zone: dict[int, dict] = {}
    vuln_by_zone: dict[int, dict] = {}
    for zone in zones:
        zd = readings_by_zone.get(zone.id, {})
        risk_by_zone[zone.id] = risk_engine.score_zone(
            zone.code, zone.name,
            rainfall_mm=zd.get("rainfall_mm", 0.0),
            water_level_m=zd.get("water_level_m", 0.0),
            elevation_tier=zone.elevation_tier.value,
            severity=severity,
        )
        vuln_by_zone[zone.id] = score_vulnerability(zone)

    # 3. Routing: apply this tick's flood impact, then find each zone's
    # route to its nearest shelter
    mobility_engine = _get_mobility_engine(run.id, zones, roads, shelters)
    mobility_engine.apply_flood_impact({zid: r["score"] for zid, r in risk_by_zone.items()})

    routes_by_zone = {zone.id: mobility_engine.get_route_to_nearest_shelter(zone.id) for zone in zones}

    # 4. Persist the tick first -- everything below depends on tick.id existing
    raw_state = {
        "tick": next_tick_number,
        "scenario_type": scenario.scenario_type,
        "readings": [{"zone_id": r.zone_id, "event_type": r.event_type, "value": r.value} for r in readings],
        "risk_scores": {zid: r["score"] for zid, r in risk_by_zone.items()},
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

    # 5. Now write the per-zone rows, all pointing at the real tick.id
    for zone in zones:
        result = risk_by_zone[zone.id]
        session.add(RiskScore(
            simulation_tick_id=tick.id, zone_id=zone.id,
            score=result["score"], risk_level=result["risk_level"],
            confidence=result["confidence"], reason=result["reason"],
        ))

        vuln_result = vuln_by_zone[zone.id]
        session.add(VulnerabilityScore(
            simulation_tick_id=tick.id, zone_id=zone.id,
            score=vuln_result["score"], tier=vuln_result["tier"],
            rationale_json=vuln_result["rationale_json"],
        ))

        route = routes_by_zone[zone.id]
        if route.get("to_shelter_id") is not None:
            session.add(RouteOption(
                simulation_tick_id=tick.id, from_zone_id=zone.id,
                to_shelter_id=route["to_shelter_id"], path_json={"path": route["path"]},
                eta=route["distance_km"] or 0.0, status=route["status"],
            ))

    session.commit()

    # 6. Check if this tick warrants a replan -- if so, generate a plan
    # and turn it into pending recommendations. Nothing here executes
    # anything on its own; that only happens once a human approves.
    trigger = trigger_evaluator.evaluate_tick(next_tick_number, risk_by_zone, routes_by_zone)
    if trigger is not None:
        governor = _get_governor(run.id)
        zone_states = [
            ZoneState(
                zone.id, zone.code, zone.name, zone.population, zone.elderly_pct,
                risk_by_zone[zone.id]["score"], vuln_by_zone[zone.id]["score"],
                risk_by_zone[zone.id]["time_to_critical"],
            )
            for zone in zones
        ]
        shelter_states = [ShelterState(s.id, s.name, s.capacity, s.current_occupancy) for s in shelters]

        plan = governor.handle_replan(trigger, zone_states, routes_by_zone, shelter_states)
        recommendation_service.create_from_plan(session, run.id, tick.id, plan)

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
    _risk_engines.pop(run.id, None)
    _mobility_engines.pop(run.id, None)
    _governors.pop(run.id, None)
    return run
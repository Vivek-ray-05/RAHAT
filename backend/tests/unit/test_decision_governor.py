from app.core.enums import RouteStatus
from app.engines.governor.decision_governor import DecisionGovernor, ShelterState, ZoneState


def _zone(zone_id, risk=5.0, vuln=5.0, population=1000, elderly_pct=8.0, ttc=99):
    return ZoneState(zone_id, f"Z{zone_id:02d}", f"Zone {zone_id}", population, elderly_pct, risk, vuln, ttc)


def _usable_route(zone_id, shelter_id):
    return {"from_zone_id": zone_id, "to_shelter_id": shelter_id, "path": [], "distance_km": 1.0, "status": RouteStatus.USABLE}


def test_higher_risk_zone_ranks_first():
    governor = DecisionGovernor()
    zones = [_zone(1, risk=2.0), _zone(2, risk=9.0)]
    routes = {1: _usable_route(1, 10), 2: _usable_route(2, 10)}
    ranked = governor.rank_zones(zones, routes)
    assert ranked[0]["zone"].zone_id == 2
    assert ranked[0]["rank"] == 1


def test_blocked_route_scores_lower_than_usable_route_all_else_equal():
    governor = DecisionGovernor()
    zones = [_zone(1, risk=5.0), _zone(2, risk=5.0)]
    routes = {
        1: _usable_route(1, 10),
        2: {"from_zone_id": 2, "to_shelter_id": None, "path": [], "distance_km": None, "status": RouteStatus.BLOCKED},
    }
    ranked = governor.rank_zones(zones, routes)
    scored = {item["zone"].zone_id: item["priority_score"] for item in ranked}
    assert scored[1] > scored[2]


def test_plan_assigns_population_up_to_shelter_capacity():
    governor = DecisionGovernor()
    zones = [_zone(1, population=800)]
    routes = {1: _usable_route(1, 10)}
    shelters = [ShelterState(10, "Shelter", capacity=500, current_occupancy=0)]
    ranked = governor.rank_zones(zones, routes)
    plan = governor.generate_evacuation_plan(ranked, shelters)
    entry = plan["evacuation_sequence"][0]
    assert entry["assigned_shelter_id"] == 10
    assert entry["assigned_population"] == 500


def test_plan_leaves_zone_unassigned_when_shelter_is_already_full():
    governor = DecisionGovernor()
    zones = [_zone(1, population=200)]
    routes = {1: _usable_route(1, 10)}
    shelters = [ShelterState(10, "Shelter", capacity=500, current_occupancy=500)]
    ranked = governor.rank_zones(zones, routes)
    plan = governor.generate_evacuation_plan(ranked, shelters)
    entry = plan["evacuation_sequence"][0]
    assert entry["assigned_shelter_id"] is None
    assert entry["assigned_population"] == 0
    assert "full" in entry["reason"]


def test_two_zones_sharing_a_shelter_split_remaining_capacity_in_rank_order():
    governor = DecisionGovernor()
    zones = [_zone(1, risk=9.0, population=400), _zone(2, risk=1.0, population=400)]
    routes = {1: _usable_route(1, 10), 2: _usable_route(2, 10)}
    shelters = [ShelterState(10, "Shelter", capacity=600, current_occupancy=0)]
    ranked = governor.rank_zones(zones, routes)
    plan = governor.generate_evacuation_plan(ranked, shelters)
    by_zone = {e["zone_id"]: e for e in plan["evacuation_sequence"]}
    assert by_zone[1]["assigned_population"] == 400  # higher-risk zone goes first, gets full request
    assert by_zone[2]["assigned_population"] == 200  # only 200 capacity left


def test_replan_within_cooldown_returns_the_same_plan():
    governor = DecisionGovernor(replan_cooldown_ticks=3)
    zones = [_zone(1)]
    routes = {1: _usable_route(1, 10)}
    shelters = [ShelterState(10, "Shelter", capacity=500)]

    first = governor.handle_replan({"trigger_type": "risk_threshold", "tick": 0}, zones, routes, shelters)
    second = governor.handle_replan({"trigger_type": "risk_threshold", "tick": 1}, zones, routes, shelters)
    assert first is second


def test_replan_after_cooldown_generates_a_new_plan():
    governor = DecisionGovernor(replan_cooldown_ticks=2)
    zones = [_zone(1)]
    routes = {1: _usable_route(1, 10)}
    shelters = [ShelterState(10, "Shelter", capacity=500)]

    first = governor.handle_replan({"trigger_type": "risk_threshold", "tick": 0}, zones, routes, shelters)
    second = governor.handle_replan({"trigger_type": "risk_threshold", "tick": 5}, zones, routes, shelters)
    assert first is not second


def test_manual_emergency_bypasses_cooldown():
    governor = DecisionGovernor(replan_cooldown_ticks=10)
    zones = [_zone(1)]
    routes = {1: _usable_route(1, 10)}
    shelters = [ShelterState(10, "Shelter", capacity=500)]

    first = governor.handle_replan({"trigger_type": "risk_threshold", "tick": 0}, zones, routes, shelters)
    second = governor.handle_replan({"trigger_type": "manual_emergency", "tick": 1}, zones, routes, shelters)
    assert first is not second

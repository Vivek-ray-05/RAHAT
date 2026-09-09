from app.core.enums import ElevationTier, RouteStatus
from app.engines.mobility.mobility_agent import MobilityEngine
from app.models.road import Road
from app.models.shelter import Shelter
from app.models.zone import Zone


def _zone(zone_id: int) -> Zone:
    return Zone(
        id=zone_id, name=f"Zone {zone_id}", code=f"Z{zone_id:02d}",
        elevation_tier=ElevationTier.MID, population=1000, elderly_pct=5.0,
    )


def _network_with_alt_path():
    """A -- 1km -- C (shelter here), plus a longer detour A -- B -- C."""
    zones = [_zone(1), _zone(2), _zone(3)]
    shelters = [Shelter(id=10, code="S1", name="Shelter", zone_id=3, capacity=500, current_occupancy=0)]
    roads = [
        Road(id=1, from_zone_id=1, to_zone_id=3, distance_km=1.0),
        Road(id=2, from_zone_id=1, to_zone_id=2, distance_km=1.0),
        Road(id=3, from_zone_id=2, to_zone_id=3, distance_km=1.0),
    ]
    return MobilityEngine(zones, roads, shelters)


def _network_with_dead_end():
    """A -- 1km -- C (shelter here); A -- B is a dead end (no B-C road)."""
    zones = [_zone(1), _zone(2), _zone(3)]
    shelters = [Shelter(id=10, code="S1", name="Shelter", zone_id=3, capacity=500, current_occupancy=0)]
    roads = [
        Road(id=1, from_zone_id=1, to_zone_id=3, distance_km=1.0),
        Road(id=2, from_zone_id=1, to_zone_id=2, distance_km=1.0),
    ]
    return MobilityEngine(zones, roads, shelters)


def test_direct_route_is_usable():
    engine = _network_with_alt_path()
    route = engine.get_route(1, 10)
    assert route["status"] == RouteStatus.USABLE
    assert route["path"] == ["zone:1", "zone:3", "shelter:10"]


def test_route_to_zone_with_its_own_shelter_is_the_short_access_edge():
    engine = _network_with_alt_path()
    route = engine.get_route(3, 10)
    assert route["status"] == RouteStatus.USABLE
    assert route["distance_km"] == 0.5


def test_no_path_at_all_is_blocked():
    engine = _network_with_dead_end()
    engine.mark_road_blocked(1, 3)
    route = engine.get_route(1, 10)
    assert route["status"] == RouteStatus.BLOCKED
    assert route["path"] == []


def test_manual_block_forces_a_real_detour_and_degrades_status():
    engine = _network_with_alt_path()
    engine.mark_road_blocked(1, 3)
    route = engine.get_route(1, 10)
    assert route["status"] == RouteStatus.DEGRADED
    assert route["path"] == ["zone:1", "zone:2", "zone:3", "shelter:10"]


def test_manual_block_survives_a_flood_impact_recompute():
    """apply_flood_impact rebuilds the live graph from scratch every
    tick -- a manual block must still be honored afterward, or a road
    an NDRF team reported as impassable would silently reopen."""
    engine = _network_with_alt_path()
    engine.mark_road_blocked(1, 3)
    engine.apply_flood_impact({1: 0.0, 2: 0.0, 3: 0.0})
    route = engine.get_route(1, 10)
    assert route["status"] == RouteStatus.DEGRADED


def test_flood_impact_removes_edges_touching_a_high_risk_zone():
    engine = _network_with_dead_end()
    engine.apply_flood_impact({1: 10.0, 2: 0.0, 3: 0.0})
    route = engine.get_route(1, 10)
    assert route["status"] == RouteStatus.BLOCKED


def test_flood_impact_does_not_touch_an_unrelated_zones_route():
    """Regression check for the detour-ratio fix: flooding zone 2
    must not degrade zone 1's already-short direct route to zone 3."""
    engine = _network_with_alt_path()
    engine.apply_flood_impact({1: 0.0, 2: 10.0, 3: 0.0})
    route = engine.get_route(1, 10)
    assert route["status"] == RouteStatus.USABLE


def test_get_route_to_nearest_shelter_picks_the_closer_of_two():
    zones = [_zone(1), _zone(2), _zone(3)]
    roads = [
        Road(id=1, from_zone_id=1, to_zone_id=3, distance_km=1.0),
        Road(id=2, from_zone_id=1, to_zone_id=2, distance_km=5.0),
    ]
    shelters = [
        Shelter(id=10, code="S1", name="Near Shelter", zone_id=3, capacity=500, current_occupancy=0),
        Shelter(id=11, code="S2", name="Far Shelter", zone_id=2, capacity=500, current_occupancy=0),
    ]
    engine = MobilityEngine(zones, roads, shelters)
    best = engine.get_route_to_nearest_shelter(1)
    assert best["to_shelter_id"] == 10

"""
Builds real Road connections between seeded zones using an actual
Bengaluru drivable road network (OSMnx/OpenStreetMap), replacing the
seed script's old single hand-picked Marathahalli<->Bellandur road.

The road network itself (backend/data/bengaluru_roads.graphml, ~166MB,
180k+ nodes) is downloaded once and cached locally -- it's gitignored,
not committed, since it's a large regeneratable derived artifact, not
source data. First run takes several minutes; later runs load the
cached file in under a minute.

For each zone, its center is snapped to the nearest real road-network
node, and a road is created to its K nearest other zones by real
road-network distance (not straight-line) -- not a full N-squared mesh
between every zone, which wouldn't reflect real city topology and
would make routing trivial. Capacity is derived from the OSM
highway-class and lane-count tags along the path, taking the
bottleneck (minimum) segment.
"""
import ast
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import networkx as nx
import osmnx as ox
from sqlmodel import Session, select

from app.db.session import engine, init_db
from app.models import (  # noqa: F401
    user, zone, shelter, road, scenario, simulation,
    sensor_event, citizen_report, risk_score, vulnerability_score, route_option,
)
from app.models.zone import Zone
from app.models.road import Road

GRAPH_PATH = Path(__file__).resolve().parents[1] / "data" / "bengaluru_roads.graphml"

# Bounding box covering all 28 seeded zone centers, with ~0.03deg (~3km) margin
BBOX_NORTH, BBOX_SOUTH = 13.1307, 12.8152
BBOX_EAST, BBOX_WEST = 77.7800, 77.4903

K_NEAREST_NEIGHBORS = 4  # roads created per zone, by real road distance -- not a full mesh

CAPACITY_PCU_PER_LANE = {
    "motorway": 2200, "motorway_link": 1800,
    "trunk": 1800, "trunk_link": 1500,
    "primary": 1500, "primary_link": 1200,
    "secondary": 1200, "secondary_link": 1000,
    "tertiary": 900, "tertiary_link": 800,
    "unclassified": 600, "residential": 600,
    "living_street": 400, "road": 600, "busway": 900,
}
DEFAULT_CAPACITY_PCU_PER_LANE = 600


def make_haversine_heuristic(G):
    """A* heuristic: straight-line (haversine) distance in meters,
    same unit as the 'length' edge weight. Always <= real road
    distance (roads never beat a straight line), so it's admissible --
    A* stays optimal, just explores less of the graph to get there."""
    def heuristic(u, v):
        y1, x1 = G.nodes[u]["y"], G.nodes[u]["x"]
        y2, x2 = G.nodes[v]["y"], G.nodes[v]["x"]
        R = 6371000.0  # Earth radius in meters
        phi1, phi2 = math.radians(y1), math.radians(y2)
        dphi = math.radians(y2 - y1)
        dlambda = math.radians(x2 - x1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))
    return heuristic


def get_graph() -> nx.MultiDiGraph:
    if GRAPH_PATH.exists():
        print(f"Loading cached road network from {GRAPH_PATH}...")
        t0 = time.time()
        G = ox.load_graphml(GRAPH_PATH)
        print(f"  loaded in {time.time() - t0:.1f}s: {len(G.nodes)} nodes, {len(G.edges)} edges")
        return G

    print("No cached road network found -- downloading (this takes several minutes)...")
    t0 = time.time()
    G = ox.graph_from_bbox((BBOX_WEST, BBOX_SOUTH, BBOX_EAST, BBOX_NORTH), network_type="drive")
    print(f"  downloaded in {time.time() - t0:.1f}s: {len(G.nodes)} nodes, {len(G.edges)} edges")
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, GRAPH_PATH)
    print(f"  cached to {GRAPH_PATH}")
    return G


def _parse_tag_value(value):
    """OSM tags can be a single value or a list of values (an edge
    that's been reclassified/merged). graphml round-trips lists as
    Python-literal strings, so parse those back."""
    if isinstance(value, str) and value.startswith("["):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return [value]
    if isinstance(value, list):
        return value
    return [value]


def _edge_capacity(data: dict) -> float:
    highway_values = _parse_tag_value(data.get("highway", "unclassified"))
    lane_values = _parse_tag_value(data.get("lanes", 1))

    try:
        lanes = min(int(v) for v in lane_values)
    except (ValueError, TypeError):
        lanes = 1

    per_lane_options = [CAPACITY_PCU_PER_LANE.get(str(h), DEFAULT_CAPACITY_PCU_PER_LANE) for h in highway_values]
    per_lane = min(per_lane_options)

    return per_lane * max(1, lanes)


def path_distance_km(G, node_a: int, node_b: int, heuristic) -> float:
    return nx.astar_path_length(G, node_a, node_b, heuristic=heuristic, weight="length") / 1000.0


def path_capacity(G, node_a: int, node_b: int, heuristic) -> int:
    path = nx.astar_path(G, node_a, node_b, heuristic=heuristic, weight="length")
    capacities = []
    for u, v in zip(path[:-1], path[1:]):
        edge_data = G.get_edge_data(u, v)
        # MultiDiGraph can have parallel edges between the same node
        # pair -- take the highest-capacity one (the one you'd drive on)
        best = max(_edge_capacity(d) for d in edge_data.values())
        capacities.append(best)
    return round(min(capacities)) if capacities else DEFAULT_CAPACITY_PCU_PER_LANE


def build_roads() -> None:
    init_db()
    G = get_graph()
    heuristic = make_haversine_heuristic(G)

    with Session(engine) as session:
        zones = session.exec(select(Zone)).all()
        if not zones:
            print("No zones exist -- run seed_demo_city.py first.")
            return

        print(f"Snapping {len(zones)} zones to nearest road-network nodes...")
        # Zone doesn't store lat/lon directly -- ZONE_DEFS' centers
        # aren't persisted, so they're looked up from the same list
        # seed_demo_city.py uses.
        from scripts.seed_demo_city import ZONE_DEFS
        center_by_code = {zdef["code"]: zdef["center"] for zdef in ZONE_DEFS}

        node_by_zone: dict[int, int] = {}

        for z in zones:
            center = center_by_code.get(z.code)
            if center is None:
                print(f"  WARNING: no known center for zone {z.code} ({z.name}), skipping")
                continue
            lat, lon = center
            node_by_zone[z.id] = ox.distance.nearest_nodes(G, X=lon, Y=lat)

        print("Computing real road distances between all zone pairs...")
        zone_ids = list(node_by_zone.keys())
        zones_by_id = {z.id: z for z in zones}
        distances: dict[tuple[int, int], float] = {}
        for i, a in enumerate(zone_ids):
            for b in zone_ids[i + 1:]:
                try:
                    d = path_distance_km(G, node_by_zone[a], node_by_zone[b], heuristic)
                    distances[(a, b)] = d
                    distances[(b, a)] = d
                except nx.NetworkXNoPath:
                    pass

        print(f"Clearing {session.exec(select(Road)).all().__len__()} existing Road rows "
              f"(replacing with real computed connections)...")
        for r in session.exec(select(Road)).all():
            session.delete(r)
        session.commit()

        created = 0
        for a in zone_ids:
            neighbors = sorted(
                (b for b in zone_ids if b != a and (a, b) in distances),
                key=lambda b: distances[(a, b)],
            )[:K_NEAREST_NEIGHBORS]

            for b in neighbors:
                capacity = path_capacity(G, node_by_zone[a], node_by_zone[b], heuristic)
                session.add(Road(
                    from_zone_id=a, to_zone_id=b,
                    capacity=capacity, distance_km=round(distances[(a, b)], 2),
                ))
                created += 1
                print(f"  {zones_by_id[a].name} -> {zones_by_id[b].name}: "
                      f"{distances[(a, b)]:.2f}km, capacity={capacity} pcu")

        session.commit()
        print(f"\nCreated {created} real road connections.")


if __name__ == "__main__":
    build_roads()
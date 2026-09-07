"""
Graph-based evacuation routing. Builds a road network from Zone/Road/
Shelter rows, removes edges that are flooded (zone risk over a
threshold) or manually blocked, and finds shortest paths on what's
left.

Simplified on purpose: no vehicle-count/congestion modeling yet (no
data source for it exists), no per-road flood threshold (Road has no
such field yet -- a single module-level default is used everywhere).
Both are reasonable to add later once there's real data to drive them.
"""
import networkx as nx

from app.core.enums import RouteStatus
from app.models.road import Road
from app.models.shelter import Shelter
from app.models.zone import Zone

DEFAULT_FLOOD_THRESHOLD = 0.6  # normalized 0-1; a zone at/above this floods its adjacent roads
SHELTER_ACCESS_DISTANCE_KM = 0.5  # fixed short "last mile" cost from a zone to its own shelter


def _zone_node(zone_id: int) -> str:
    return f"zone:{zone_id}"


def _shelter_node(shelter_id: int) -> str:
    return f"shelter:{shelter_id}"


class MobilityEngine:
    def __init__(self, zones: list[Zone], roads: list[Road], shelters: list[Shelter]):
        self.zones_by_id = {z.id: z for z in zones}
        self.shelters_by_id = {s.id: s for s in shelters}

        self._base_graph = nx.Graph()
        for zone in zones:
            self._base_graph.add_node(_zone_node(zone.id), kind="zone", zone_id=zone.id)

        for shelter in shelters:
            self._base_graph.add_node(_shelter_node(shelter.id), kind="shelter", shelter_id=shelter.id)
            self._base_graph.add_edge(
                _zone_node(shelter.zone_id), _shelter_node(shelter.id),
                distance_km=SHELTER_ACCESS_DISTANCE_KM, blocked=False, road_id=None,
            )

        for road in roads:
            self._base_graph.add_edge(
                _zone_node(road.from_zone_id), _zone_node(road.to_zone_id),
                distance_km=road.distance_km if road.distance_km is not None else 1.0,
                blocked=road.is_blocked, road_id=road.id,
            )

        self._live_graph = self._base_graph.copy()
        self._manually_blocked: set[tuple[str, str]] = set()

    def apply_flood_impact(self, risk_scores: dict[int, float], threshold: float = DEFAULT_FLOOD_THRESHOLD) -> None:
        """Rebuild the live graph from the base graph, dropping any edge
        touching a zone whose (normalized) risk score is at/above the
        flood threshold, plus anything manually blocked."""
        normalized = {zone_id: min(score / 10.0, 1.0) for zone_id, score in risk_scores.items()}

        self._live_graph = self._base_graph.copy()

        for u, v, data in self._base_graph.edges(data=True):
            edge_key = tuple(sorted([u, v]))

            if edge_key in self._manually_blocked or data.get("blocked"):
                if self._live_graph.has_edge(u, v):
                    self._live_graph.remove_edge(u, v)
                continue

            risk_u = normalized.get(self._node_zone_id(u), 0.0)
            risk_v = normalized.get(self._node_zone_id(v), 0.0)
            if max(risk_u, risk_v) >= threshold:
                self._live_graph.remove_edge(u, v)

    def _node_zone_id(self, node: str) -> int | None:
        data = self._base_graph.nodes[node]
        return data.get("zone_id")

    def get_route(self, from_zone_id: int, to_shelter_id: int) -> dict:
        from_node = _zone_node(from_zone_id)
        to_node = _shelter_node(to_shelter_id)

        try:
            path = nx.shortest_path(self._live_graph, from_node, to_node, weight="distance_km")
            distance = nx.shortest_path_length(self._live_graph, from_node, to_node, weight="distance_km")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return {
                "from_zone_id": from_zone_id, "to_shelter_id": to_shelter_id,
                "path": [], "distance_km": None, "status": RouteStatus.BLOCKED,
                "reason": f"No usable route from zone {from_zone_id} to shelter {to_shelter_id}.",
            }

        # Compare against the undamaged base graph to see if this is a
        # real detour, not just "something changed nearby."
        try:
            base_distance = nx.shortest_path_length(self._base_graph, from_node, to_node, weight="distance_km")
            detour_ratio = distance / base_distance if base_distance > 0 else 1.0
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            detour_ratio = 1.0  # no base-graph path to compare against; don't penalize

        status = RouteStatus.DEGRADED if detour_ratio > 1.3 else RouteStatus.USABLE

        return {
            "from_zone_id": from_zone_id, "to_shelter_id": to_shelter_id,
            "path": path, "distance_km": round(distance, 2), "status": status, "reason": "",
        }

    def get_route_to_nearest_shelter(self, from_zone_id: int) -> dict:
        candidates = [
            self.get_route(from_zone_id, shelter_id)
            for shelter_id in self.shelters_by_id
        ]
        usable = [c for c in candidates if c["status"] != RouteStatus.BLOCKED]
        if not usable:
            return {
                "from_zone_id": from_zone_id, "to_shelter_id": None,
                "path": [], "distance_km": None, "status": RouteStatus.BLOCKED,
                "reason": f"No reachable shelter from zone {from_zone_id}.",
            }
        return min(usable, key=lambda c: c["distance_km"])

    def mark_road_blocked(self, from_zone_id: int, to_zone_id: int) -> None:
        """In-memory override -- persisting this to the Road table and
        auditing who blocked it is Phase 4's job, once the approval
        workflow is the thing calling this."""
        edge_key = tuple(sorted([_zone_node(from_zone_id), _zone_node(to_zone_id)]))
        self._manually_blocked.add(edge_key)
        if self._live_graph.has_edge(*edge_key):
            self._live_graph.remove_edge(*edge_key)

    def get_graph_state(self) -> dict:
        return {
            "nodes": [{"id": n, **data} for n, data in self._live_graph.nodes(data=True)],
            "edges": [
                {"from": u, "to": v, "distance_km": data.get("distance_km")}
                for u, v, data in self._live_graph.edges(data=True)
            ],
        }
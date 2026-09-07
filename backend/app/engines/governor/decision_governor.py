"""
Combines risk, vulnerability, and route data into a ranked evacuation
plan: which zones evacuate first, and to which shelter. This produces
a recommendation only -- nothing here executes anything. Turning a
plan entry into a real action (blocking a road, committing a shelter
assignment) requires a zone admin's approval, built in Phase 4.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.enums import RouteStatus


@dataclass
class ZoneState:
    zone_id: int
    zone_code: str
    zone_name: str
    population: int
    elderly_pct: float
    risk_score: float
    vulnerability_score: float
    time_to_critical: int = 99  # ticks until risk hits 10.0; 99 = not on a critical trajectory


@dataclass
class ShelterState:
    shelter_id: int
    name: str
    capacity: int
    current_occupancy: int = 0


DEFAULT_WEIGHTS = {
    "risk": 0.40,
    "vulnerability": 0.30,
    "elderly": 0.15,
    "route_quality": 0.10,
    "urgency": 0.05,
}


class DecisionGovernor:
    def __init__(self, weights: dict | None = None, replan_cooldown_ticks: int = 2):
        self.weights = weights or DEFAULT_WEIGHTS
        self.replan_cooldown_ticks = replan_cooldown_ticks
        self._last_replan_tick = -replan_cooldown_ticks - 1  # allow the first replan to always fire
        self._last_plan: dict | None = None
        self._plan_log: list[dict] = []

    def compute_priority_score(self, zone: ZoneState, route: dict | None, weights: dict | None = None) -> float:
        w = weights or self.weights
        elderly_norm = min(zone.elderly_pct / 10.0, 10.0)  # 0-100% -> 0-10 scale
        if route and route.get("status") == RouteStatus.USABLE:
            route_quality = 10.0
        elif route and route.get("status") == RouteStatus.DEGRADED:
            route_quality = 5.0
        else:
            route_quality = 0.0
        urgency = max(0.0, 10.0 - min(zone.time_to_critical, 10))

        score = (
            w["risk"] * zone.risk_score
            + w["vulnerability"] * zone.vulnerability_score
            + w["elderly"] * elderly_norm
            + w["route_quality"] * route_quality
            + w["urgency"] * urgency
        )
        return round(score, 4)

    def rank_zones(self, zones: list[ZoneState], routes: dict[int, dict], weights: dict | None = None) -> list[dict]:
        scored = []
        for zone in zones:
            route = routes.get(zone.zone_id)
            score = self.compute_priority_score(zone, route, weights)
            scored.append({"zone": zone, "route": route, "priority_score": score})

        scored.sort(key=lambda z: z["priority_score"], reverse=True)
        for i, item in enumerate(scored):
            item["rank"] = i + 1
        return scored

    def generate_evacuation_plan(self, ranked: list[dict], shelters: list[ShelterState], tick: int = 0) -> dict:
        shelter_usage = {s.shelter_id: s.current_occupancy for s in shelters}
        shelters_by_id = {s.shelter_id: s for s in shelters}

        sequence = []
        for item in ranked:
            zone: ZoneState = item["zone"]
            route = item["route"]

            assigned_shelter_id = None
            assigned_population = 0
            reason = "No usable route to any shelter."

            if route and route.get("status") in (RouteStatus.USABLE, RouteStatus.DEGRADED) and route.get("to_shelter_id"):
                shelter_id = route["to_shelter_id"]
                shelter = shelters_by_id.get(shelter_id)
                if shelter:
                    remaining = max(0, shelter.capacity - shelter_usage.get(shelter_id, 0))
                    if remaining > 0:
                        assigned_shelter_id = shelter_id
                        assigned_population = min(zone.population, remaining)
                        shelter_usage[shelter_id] = shelter_usage.get(shelter_id, 0) + assigned_population
                        reason = (
                            f"Assigned to {shelter.name} "
                            f"({assigned_population}/{zone.population} people, {remaining} capacity available)."
                        )
                    else:
                        reason = f"Nearest shelter {shelter.name} is full."

            sequence.append({
                "rank": item["rank"],
                "zone_id": zone.zone_id,
                "zone_name": zone.zone_name,
                "priority_score": item["priority_score"],
                "risk_score": zone.risk_score,
                "vulnerability_score": zone.vulnerability_score,
                "population": zone.population,
                "assigned_shelter_id": assigned_shelter_id,
                "assigned_population": assigned_population,
                "route": route,
                "reason": reason,
            })

        plan = {
            "tick": tick,
            "evacuation_sequence": sequence,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._last_plan = plan
        self._plan_log.append(plan)
        return plan

    def handle_replan(self, trigger: dict, zones: list[ZoneState], routes: dict[int, dict], shelters: list[ShelterState]) -> dict:
        trigger_type = trigger.get("trigger_type", "unknown")
        tick = trigger.get("tick", 0)

        if trigger_type != "manual_emergency" and (tick - self._last_replan_tick) < self.replan_cooldown_ticks:
            if self._last_plan is not None:
                return self._last_plan

        self._last_replan_tick = tick
        ranked = self.rank_zones(zones, routes)
        return self.generate_evacuation_plan(ranked, shelters, tick=tick)

    def get_last_plan(self) -> dict | None:
        return self._last_plan

    def get_plan_log(self) -> list[dict]:
        return list(self._plan_log)
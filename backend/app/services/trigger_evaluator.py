"""
Looks at a tick's risk/route data and decides whether a replan should
fire, and why. The trigger dict this produces feeds directly into
DecisionGovernor.handle_replan().
"""
from app.core.enums import RouteStatus

RISK_THRESHOLD_FOR_REPLAN = 7.5


def evaluate_tick(tick_number: int, risk_by_zone: dict[int, dict], routes_by_zone: dict[int, dict]) -> dict | None:
    """Returns a trigger dict if a replan is warranted this tick, else
    None. Checks risk-threshold breaches first (more urgent), then
    route failures."""
    for zone_id, result in risk_by_zone.items():
        if result["score"] >= RISK_THRESHOLD_FOR_REPLAN:
            return {
                "trigger_type": "risk_threshold",
                "affected_zone_id": zone_id,
                "tick": tick_number,
                "detail": f"Risk score {result['score']} crossed the {RISK_THRESHOLD_FOR_REPLAN} threshold.",
            }

    for zone_id, route in routes_by_zone.items():
        if route.get("status") == RouteStatus.BLOCKED:
            return {
                "trigger_type": "route_failure",
                "affected_zone_id": zone_id,
                "tick": tick_number,
                "detail": f"No usable route from zone {zone_id} to any shelter.",
            }

    return None


def manual_trigger(zone_id: int | None, tick_number: int, reason: str = "") -> dict:
    """For an explicit human-initiated replan (e.g. a coordinator
    button) -- always bypasses the governor's cooldown."""
    return {
        "trigger_type": "manual_emergency",
        "affected_zone_id": zone_id,
        "tick": tick_number,
        "detail": reason or "Manual replan requested.",
    }
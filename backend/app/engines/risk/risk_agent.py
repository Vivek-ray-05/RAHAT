"""
Rule-based flood risk scoring: rainfall, water level, soil saturation,
and elevation combine into a 0-10 risk score per zone, with a
confidence figure and a plain-English reason.

Deterministic by design -- same inputs always produce the same score,
so a coordinator can be told exactly why a zone was ranked the way it
was, and a re-run reproduces the same result. AI is used elsewhere in
this system to explain and summarize, never to compute this number.
"""
from app.core.enums import RiskLevel


def compute_baseline_flood_risk(elevations: dict[str, float]) -> dict[str, float]:
    """A zone's inherent flood susceptibility from real elevation alone,
    independent of any live simulation tick -- this is what
    `Zone.flood_risk_base` holds, separate from RiskEngine.score_zone's
    per-tick dynamic score (which also factors in live rainfall/water
    level/soil saturation).

    Relative, not absolute: the lowest-elevation zone in the input set
    scores ~10, the highest scores ~0, everyone else lands in between
    by their real rank. Same principle as elevation_tier's relative
    thirds-split (scripts/seed_demo_city.py) -- what matters for flood
    risk is a zone's elevation relative to the others being modeled,
    not a fixed absolute cutoff that wouldn't transfer to a different
    city or a different set of seeded zones.

    A qualitative validation pass (2026-09-09) checked this exact
    approach against real Bengaluru flood history: ranking zones by
    real SRTM elevation into thirds correctly placed 10 of 12
    documented flood zones in the more-flood-prone half. The 2
    exceptions (JP Nagar, Electronic City) flood for lake-encroachment
    and stormwater-drainage reasons a center-point elevation reading
    can't see -- a known, accepted limitation, not something this
    function can fix without a real drainage/lake-proximity data
    source, which doesn't exist yet.
    """
    if not elevations:
        return {}
    if len(elevations) == 1:
        return {code: 5.0 for code in elevations}

    ranked = sorted(elevations, key=lambda code: elevations[code])
    n = len(ranked)
    return {
        code: round(10.0 * (1 - i / (n - 1)), 2)
        for i, code in enumerate(ranked)
    }


class RiskEngine:
    def __init__(self):
        self._soil_saturation: dict[str, float] = {}
        self._risk_history: dict[str, list[float]] = {}

    def compute_base_risk(
        self, rainfall_mm_hr: float, water_level_m: float, elevation_tier: str, zone_code: str,
    ) -> float:
        current_sat = self._soil_saturation.get(zone_code, 10.0)
        current_sat = min(100.0, current_sat + rainfall_mm_hr * 0.5)
        if rainfall_mm_hr < 1.0:
            current_sat = max(5.0, current_sat - 2.0)
        self._soil_saturation[zone_code] = current_sat

        rain_component = rainfall_mm_hr / 20.0
        water_component = water_level_m * 2.0
        sat_component = current_sat / 50.0

        base_risk = rain_component + water_component + sat_component

        elevation_modifiers = {"high": 0.6, "mid": 1.0, "low": 1.5}
        modifier = elevation_modifiers.get(elevation_tier, 1.0)

        return round(max(0.0, min(10.0, base_risk * modifier)), 2)

    def _compute_time_to_critical(self, zone_code: str, current_score: float) -> int:
        history = self._risk_history.get(zone_code, [])
        if current_score >= 10.0:
            return 0
        if len(history) < 2:
            return 99

        deltas = [history[i] - history[i - 1] for i in range(1, len(history))]
        avg_rate = sum(deltas) / len(deltas)
        if avg_rate <= 0.01:
            return 99

        return max(1, round((10.0 - current_score) / avg_rate))

    @staticmethod
    def _compute_confidence(rainfall: float, water_level: float) -> float:
        signal_strength = min((rainfall / 50.0 + water_level / 2.0) / 2.0, 1.0)
        return round(0.70 + signal_strength * 0.20, 2)

    @staticmethod
    def risk_level(score: float) -> RiskLevel:
        if score >= 9.0:
            return RiskLevel.CRITICAL
        elif score >= 7.0:
            return RiskLevel.HIGH
        elif score >= 4.0:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def default_reason(zone_name: str, score: float) -> str:
        level = RiskEngine.risk_level(score).value
        return f"{zone_name} shows {level} risk (score: {score:.1f}/10)."

    def score_zone(
        self, zone_code: str, zone_name: str, rainfall_mm: float, water_level_m: float,
        elevation_tier: str, severity: float = 1.0,
    ) -> dict:
        base = self.compute_base_risk(rainfall_mm, water_level_m, elevation_tier, zone_code)
        score = round(max(0.0, min(10.0, base * severity)), 2)

        self._risk_history.setdefault(zone_code, [])
        self._risk_history[zone_code].append(score)
        self._risk_history[zone_code] = self._risk_history[zone_code][-5:]

        return {
            "score": score,
            "risk_level": self.risk_level(score),
            "confidence": self._compute_confidence(rainfall_mm, water_level_m),
            "reason": self.default_reason(zone_name, score),
            "time_to_critical": self._compute_time_to_critical(zone_code, score),
        }
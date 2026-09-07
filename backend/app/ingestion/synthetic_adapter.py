"""
Generates synthetic rainfall/water-level readings for a scenario tick.
No real sensors exist yet -- this is what feeds the risk engine until
a real adapter (Phase 7) is wired in.

Design: rainfall and water level both rise with tick number (a flood
getting worse over time), scaled by a severity multiplier from the
scenario's config, plus a small random wobble so zones don't move in
lockstep. This is a deliberately simple model -- not modeling real
hydrology -- good enough to drive the risk engine's rule-based scoring
with plausible, gradually-worsening numbers.
"""
import random

from datetime import datetime, timezone

from app.ingestion.base import AbstractIngestionAdapter, NormalizedEvent


class SyntheticFloodAdapter(AbstractIngestionAdapter):
    source_name = "synthetic"

    def __init__(self, zone_ids: list[int], tick: int, severity: float = 1.0,
                 simulation_run_id: int | None = None):
        self.zone_ids = zone_ids
        self.tick = tick
        self.severity = severity
        self.simulation_run_id = simulation_run_id

    def poll_or_receive(self) -> list[dict]:
        readings = []
        for zone_id in self.zone_ids:
            base_rainfall = min(5 + self.tick * 1.2, 60) * self.severity
            base_water_level = min(0.1 + self.tick * 0.05, 3.5) * self.severity

            readings.append({
                "zone_id": zone_id,
                "event_type": "rainfall_mm",
                "value": max(0.0, base_rainfall + random.uniform(-2, 2)),
            })
            readings.append({
                "zone_id": zone_id,
                "event_type": "water_level_m",
                "value": max(0.0, base_water_level + random.uniform(-0.1, 0.1)),
            })
        return readings

    def normalize(self, raw: dict) -> NormalizedEvent:
        return NormalizedEvent(
            source=self.source_name,
            zone_id=raw["zone_id"],
            event_type=raw["event_type"],
            value=raw["value"],
            confidence=1.0,  # synthetic data is "certain" by construction
            observed_at=datetime.now(timezone.utc),
            provenance={"generator": "SyntheticFloodAdapter", "tick": self.tick, "severity": self.severity},
            simulation_run_id=self.simulation_run_id,
        )

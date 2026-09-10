"""
Real HTTP ingestion adapter -- polls Open-Meteo's free, no-API-key
weather API (api.open-meteo.com) for real current rainfall at each
zone's real coordinates. Same real-data-over-synthetic principle as
the rest of this project (OSM for roads/buildings, SRTM for
elevation) -- Open-Meteo was picked for the same reason those were:
free, no signup, no key, reliable enough for a non-institutional
build.

Not wired into the live tick loop yet -- `SyntheticFloodAdapter`
stays the default there, since the tick loop is built around
deterministic, reproducible scenarios (same seed -> same ticks),
which real live weather can't offer. This adapter is for a genuinely
different use case: pulling real current conditions for a zone
outside of a scripted scenario, e.g. a future "what's actually
happening right now" view. It fully implements
`AbstractIngestionAdapter` and is ready to be pointed at real zone
coordinates whenever that's wired up.
"""
import json
import urllib.error
import urllib.request

from datetime import datetime, timezone

from app.ingestion.base import AbstractIngestionAdapter, NormalizedEvent

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "RAHAT-http-adapter/1.0"
REQUEST_TIMEOUT_SECONDS = 10


class HttpWeatherAdapter(AbstractIngestionAdapter):
    source_name = "open_meteo_http"

    def __init__(self, zone_coords: dict[int, tuple[float, float]], simulation_run_id: int | None = None):
        """zone_coords: {zone_id: (latitude, longitude)} -- the caller
        supplies real coordinates (e.g. from the same ZONE_DEFS
        scripts/seed_demo_city.py already has), same pattern as
        SyntheticFloodAdapter taking a plain zone_ids list rather than
        querying the DB itself."""
        self.zone_coords = zone_coords
        self.simulation_run_id = simulation_run_id

    def poll_or_receive(self) -> list[dict]:
        readings = []
        for zone_id, (lat, lon) in self.zone_coords.items():
            current = self._fetch_current_conditions(lat, lon)
            if current is None:
                continue
            readings.append({
                "zone_id": zone_id,
                "event_type": "rainfall_mm",
                "value": float(current.get("precipitation", 0.0)),
                "raw": current,
            })
        return readings

    def _fetch_current_conditions(self, lat: float, lon: float) -> dict | None:
        url = (
            f"{OPEN_METEO_URL}?latitude={lat}&longitude={lon}"
            "&current=precipitation,rain,temperature_2m&timezone=auto"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                body = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, ValueError):
            # A live weather API being unreachable shouldn't crash a
            # tick -- treat it the same as "no reading this round" and
            # let the caller fall back to whatever else it has.
            return None
        return body.get("current")

    def normalize(self, raw: dict) -> NormalizedEvent:
        return NormalizedEvent(
            source=self.source_name,
            zone_id=raw["zone_id"],
            event_type=raw["event_type"],
            value=raw["value"],
            confidence=0.9,  # a real measurement, but one point for the whole zone, not hyperlocal
            observed_at=datetime.now(timezone.utc),
            provenance={"provider": "open-meteo.com", "raw": raw.get("raw", {})},
            simulation_run_id=self.simulation_run_id,
        )

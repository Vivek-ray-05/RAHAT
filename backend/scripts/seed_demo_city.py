"""
Seeds real Bengaluru localities using actual OpenStreetMap data: real
building counts (via a live Overpass count query) for a population
estimate, real hospitals/schools/community centres, and real
elevation from SRTM (via opentopodata.org). 28 real, well-known
Bengaluru localities, not the 198 official administrative wards --
enough for a genuine city-scale dataset without being an
administrative exercise.

What's real: locality names and centers, hospital counts, named
shelter candidates (schools/community halls -- the actual real-world
convention for designated flood-relief shelters in Bengaluru),
building-derived population estimate, and per-zone elevation in
meters.

What's estimated, and clearly labeled as such: population (building
count x an assumed occupancy figure, not a census number), elderly_pct
(a single citywide estimate, no per-locality source available yet),
and shelter capacity (OSM has no capacity data for these buildings).

elevation_tier is computed by ranking every seeded zone's real
elevation and splitting into thirds -- what matters for flood risk is
a zone's elevation relative to the others being modeled, not an
arbitrary absolute cutoff. Re-running this script with a different
set of zones will re-rank everyone -- that's intentional, not a bug.

Road connectivity between zones is NOT built here -- that comes from
a real road network (OSMnx), which will also replace the single
hand-picked Marathahalli<->Bellandur road this script used to create
originally.

The public Overpass instance is shared and sometimes overloaded
(429/504 responses) -- every live query here retries with backoff,
and large requests are split into small batches rather than one huge
request, since that's what was actually timing out in practice.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.db.session import engine, init_db
from app.core.enums import ElevationTier
from app.models import (  # noqa: F401 -- import so tables register
    user, zone, shelter, road, scenario, simulation,
    sensor_event, citizen_report, risk_score, vulnerability_score, route_option,
)
from app.models.zone import Zone
from app.models.shelter import Shelter

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OPENTOPODATA_URL = "https://api.opentopodata.org/v1/srtm30m"
USER_AGENT = "RAHAT-seed-script/1.0 (contact: dishaagarwal023@gmail.com)"

BUILDING_COUNT_RADIUS_M = 1500
AMENITY_BATCH_SIZE = 4  # zones per Overpass amenities request -- 28 in one request timed out
MAX_RETRIES = 3
ASSUMED_OCCUPANTS_PER_BUILDING = 4  # documented estimate, not a real demographic figure
DEFAULT_SHELTER_CAPACITY = 500  # estimate -- OSM has no capacity data
CITYWIDE_ELDERLY_PCT = 8.0  # single citywide estimate, no per-locality source available yet

# Per-field provenance, identical for every seeded zone since they all
# go through the same pipeline -- surfaced to the UI so a coordinator
# can tell a real number (SRTM elevation, OSM hospital count) from an
# estimate (building-derived population, a single citywide elderly_pct)
# until a real institutional data partnership replaces the estimates.
DATA_QUALITY_NOTES = {
    "population": {
        "quality": "estimated",
        "note": f"OSM building count within {BUILDING_COUNT_RADIUS_M}m x {ASSUMED_OCCUPANTS_PER_BUILDING} assumed occupants/building -- not a census figure",
    },
    "elderly_pct": {
        "quality": "estimated",
        "note": f"single citywide figure ({CITYWIDE_ELDERLY_PCT}%), no per-locality source available yet",
    },
    "population_density": {
        "quality": "unavailable",
        "note": "not computed -- no reliable zone-boundary (area) source yet",
    },
    "elevation_m": {
        "quality": "real",
        "note": "SRTM 30m via opentopodata.org",
    },
    "elevation_tier": {
        "quality": "derived",
        "note": "ranked from real elevation_m across all seeded zones, split into thirds -- relative, not an absolute cutoff",
    },
    "area_km2": {
        "quality": "unavailable",
        "note": "not computed -- no reliable zone-boundary source yet",
    },
    "hospital_count": {
        "quality": "real",
        "note": f"OSM Overpass amenity=hospital within {BUILDING_COUNT_RADIUS_M}m radius",
    },
    "flood_risk_base": {
        "quality": "unavailable",
        "note": "not yet computed -- reserved for a future baseline model",
    },
}

ZONE_DEFS = [
    {"code": "Z01", "name": "Marathahalli", "center": (12.9591, 77.6974)},
    {"code": "Z02", "name": "Bellandur", "center": (12.9304, 77.6784)},
    {"code": "Z03", "name": "Indiranagar", "center": (12.9719, 77.6412)},
    {"code": "Z04", "name": "Koramangala", "center": (12.9352, 77.6245)},
    {"code": "Z05", "name": "HSR Layout", "center": (12.9121, 77.6446)},
    {"code": "Z06", "name": "Whitefield", "center": (12.9698, 77.7500)},
    {"code": "Z07", "name": "Electronic City", "center": (12.8452, 77.6602)},
    {"code": "Z08", "name": "Jayanagar", "center": (12.9250, 77.5938)},
    {"code": "Z09", "name": "Malleswaram", "center": (13.0027, 77.5709)},
    {"code": "Z10", "name": "Yelahanka", "center": (13.1007, 77.5963)},
    {"code": "Z11", "name": "Sarjapur Road", "center": (12.9105, 77.6879)},
    {"code": "Z12", "name": "Hebbal", "center": (13.0358, 77.5970)},
    {"code": "Z13", "name": "RT Nagar", "center": (13.0198, 77.5938)},
    {"code": "Z14", "name": "Rajajinagar", "center": (12.9911, 77.5529)},
    {"code": "Z15", "name": "Basavanagudi", "center": (12.9422, 77.5760)},
    {"code": "Z16", "name": "Banashankari", "center": (12.9255, 77.5468)},
    {"code": "Z17", "name": "Vijayanagar", "center": (12.9719, 77.5300)},
    {"code": "Z18", "name": "CV Raman Nagar", "center": (12.9880, 77.6636)},
    {"code": "Z19", "name": "Domlur", "center": (12.9611, 77.6387)},
    {"code": "Z20", "name": "Ulsoor", "center": (12.9815, 77.6205)},
    {"code": "Z21", "name": "Frazer Town", "center": (12.9967, 77.6119)},
    {"code": "Z22", "name": "JP Nagar", "center": (12.9077, 77.5851)},
    {"code": "Z23", "name": "BTM Layout", "center": (12.9166, 77.6101)},
    {"code": "Z24", "name": "Krishnarajapuram", "center": (13.0027, 77.6959)},
    {"code": "Z25", "name": "Bommanahalli", "center": (12.8990, 77.6228)},
    {"code": "Z26", "name": "Peenya", "center": (13.0286, 77.5203)},
    {"code": "Z27", "name": "Yeshwanthpur", "center": (13.0284, 77.5540)},
    {"code": "Z28", "name": "Banaswadi", "center": (13.0140, 77.6494)},
]


def _fetch_json_with_retry(req: urllib.request.Request, timeout: int) -> dict | None:
    """POST/GET a request, retrying with backoff on failure. Returns
    None (caller decides the fallback) if every attempt fails."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"  request failed after {MAX_RETRIES} attempts: {e}")
                return None
            wait = 3 * attempt
            print(f"  request failed ({e}), retrying in {wait}s (attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(wait)
    return None


def fetch_building_count(lat: float, lon: float) -> int:
    query = f"""
    [out:json][timeout:25];
    (
      way["building"](around:{BUILDING_COUNT_RADIUS_M},{lat},{lon});
      node["building"](around:{BUILDING_COUNT_RADIUS_M},{lat},{lon});
    );
    out count;
    """
    req = urllib.request.Request(
        OVERPASS_URL, data=query.encode("utf-8"), method="POST",
        headers={"User-Agent": USER_AGENT},
    )
    data = _fetch_json_with_retry(req, timeout=30)
    if data is None:
        return 0
    elements = data.get("elements", [])
    if elements and "tags" in elements[0]:
        return int(elements[0]["tags"].get("total", 0))
    return 0


def fetch_real_amenities_batched() -> list[dict]:
    """Live Overpass query for real hospitals/schools/community
    centres, split into small batches of AMENITY_BATCH_SIZE zones per
    request -- one big request for all 28 zones timed out in practice."""
    all_elements: list[dict] = []
    for i in range(0, len(ZONE_DEFS), AMENITY_BATCH_SIZE):
        batch = ZONE_DEFS[i:i + AMENITY_BATCH_SIZE]
        around_clauses = "\n".join(
            f'  node["amenity"~"hospital|school|community_centre"](around:2000,{lat},{lon});'
            for lat, lon in (z["center"] for z in batch)
        )
        query = f"""
        [out:json][timeout:40];
        (
        {around_clauses}
        );
        out body;
        """
        req = urllib.request.Request(
            OVERPASS_URL, data=query.encode("utf-8"), method="POST",
            headers={"User-Agent": USER_AGENT},
        )
        print(f"  amenities batch {i // AMENITY_BATCH_SIZE + 1} "
              f"({', '.join(z['name'] for z in batch)})...")
        data = _fetch_json_with_retry(req, timeout=60)
        if data:
            all_elements.extend(data.get("elements", []))
        time.sleep(2)
    return all_elements


def fetch_elevations() -> dict[str, float]:
    locations = "|".join(f"{lat},{lon}" for lat, lon in (z["center"] for z in ZONE_DEFS))
    url = f"{OPENTOPODATA_URL}?locations={locations}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    data = _fetch_json_with_retry(req, timeout=30)
    if data is None:
        print("WARNING: opentopodata unreachable; all zones will get elevation_m=0.0")
        return {zdef["code"]: 0.0 for zdef in ZONE_DEFS}
    return {zdef["code"]: result["elevation"] for zdef, result in zip(ZONE_DEFS, data["results"])}


def classify_elevation_tiers(elevations: dict[str, float]) -> dict[str, ElevationTier]:
    sorted_codes = sorted(elevations, key=lambda c: elevations[c])
    n = len(sorted_codes)
    edge_cut = max(1, round(n / 3))

    tiers: dict[str, ElevationTier] = {}
    for i, code in enumerate(sorted_codes):
        if i < edge_cut:
            tiers[code] = ElevationTier.LOW
        elif i >= n - edge_cut:
            tiers[code] = ElevationTier.HIGH
        else:
            tiers[code] = ElevationTier.MID
    return tiers


def nearest_zone_code(lat: float, lon: float) -> str:
    def dist(z):
        clat, clon = z["center"]
        return ((lat - clat) ** 2 + (lon - clon) ** 2) ** 0.5

    return min(ZONE_DEFS, key=dist)["code"]


def seed() -> None:
    init_db()

    print(f"Fetching real amenities for {len(ZONE_DEFS)} zones from Overpass (batched)...")
    amenities = fetch_real_amenities_batched()

    print("Fetching real elevation from opentopodata...")
    elevations = fetch_elevations()
    elevation_tiers = classify_elevation_tiers(elevations)

    hospital_counts: dict[str, int] = {z["code"]: 0 for z in ZONE_DEFS}
    shelter_candidates: dict[str, list[str]] = {z["code"]: [] for z in ZONE_DEFS}
    for el in amenities:
        tags = el.get("tags", {})
        amenity = tags.get("amenity")
        name = tags.get("name")
        code = nearest_zone_code(el["lat"], el["lon"])

        if amenity == "hospital":
            hospital_counts[code] += 1
        elif amenity in ("school", "community_centre") and name:
            shelter_candidates[code].append(name)

    print("Fetching real building counts for population estimates...")
    building_counts: dict[str, int] = {}
    for i, zdef in enumerate(ZONE_DEFS):
        lat, lon = zdef["center"]
        print(f"  {zdef['name']} ({i + 1}/{len(ZONE_DEFS)})...")
        building_counts[zdef["code"]] = fetch_building_count(lat, lon)
        time.sleep(2)

    with Session(engine) as session:
        zones_by_code: dict[str, Zone] = {}

        for zdef in ZONE_DEFS:
            code = zdef["code"]
            building_count = building_counts[code]
            population_estimate = building_count * ASSUMED_OCCUPANTS_PER_BUILDING

            existing = session.exec(select(Zone).where(Zone.code == code)).first()
            if existing:
                existing.population = population_estimate
                existing.hospital_count = hospital_counts[code]
                existing.elevation_m = round(elevations[code])
                existing.elevation_tier = elevation_tiers[code]
                existing.data_quality_json = DATA_QUALITY_NOTES
                session.add(existing)
                session.commit()
                session.refresh(existing)
                zones_by_code[code] = existing
                print(f"Updated zone {code} ({existing.name}): population~{population_estimate} "
                      f"(from {building_count} buildings), hospital_count={existing.hospital_count}, "
                      f"elevation_m={existing.elevation_m} (tier={existing.elevation_tier.value})")
                continue

            z = Zone(
                code=code, name=zdef["name"], population=population_estimate,
                elderly_pct=CITYWIDE_ELDERLY_PCT, population_density=None,
                elevation_tier=elevation_tiers[code], elevation_m=round(elevations[code]),
                hospital_count=hospital_counts[code], flood_risk_base=None,
                data_quality_json=DATA_QUALITY_NOTES,
            )
            session.add(z)
            session.commit()
            session.refresh(z)
            zones_by_code[code] = z
            print(f"Created zone {z.code} ({z.name}): population~{population_estimate} "
                  f"(from {building_count} buildings), real hospital_count={z.hospital_count}, "
                  f"real elevation_m={z.elevation_m} (tier={z.elevation_tier.value})")

        # Replace any placeholder shelters with real ones now that we
        # have real candidate names for that zone.
        for zdef in ZONE_DEFS:
            code = zdef["code"]
            if not shelter_candidates[code]:
                continue
            zone_ = zones_by_code[code]
            placeholders = session.exec(
                select(Shelter).where(Shelter.zone_id == zone_.id, Shelter.name.like("[PLACEHOLDER]%"))
            ).all()
            for p in placeholders:
                session.delete(p)
            if placeholders:
                session.commit()
                print(f"Removed {len(placeholders)} placeholder shelter(s) for {zdef['name']}")

        existing_codes = session.exec(select(Shelter.code)).all()
        next_num = max((int(c[1:]) for c in existing_codes), default=0) + 1

        for zdef in ZONE_DEFS:
            code = zdef["code"]
            zone_ = zones_by_code[code]
            names = shelter_candidates[code][:2]  # cap at 2 per zone for a manageable dataset

            existing_for_zone = session.exec(select(Shelter).where(Shelter.zone_id == zone_.id)).all()
            if existing_for_zone:
                continue  # already has real (or still-placeholder, unresolved) shelters

            if not names:
                names = [f"[PLACEHOLDER] {zdef['name']} Community Shelter"]

            for name in names:
                shelter_code = f"S{next_num:02d}"
                next_num += 1
                session.add(Shelter(
                    code=shelter_code, name=name, zone_id=zone_.id,
                    capacity=DEFAULT_SHELTER_CAPACITY, has_medical=False,
                ))
                session.commit()
                print(f"Created shelter {shelter_code}: {name} ({zdef['name']})")


if __name__ == "__main__":
    seed()
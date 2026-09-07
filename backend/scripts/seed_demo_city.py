"""
Seeds real Bengaluru localities using actual OpenStreetMap data: real
road names from the geojson extracts (backend/data/*.geojson), real
hospitals/schools/community centres pulled live from the Overpass
API, and real elevation from SRTM (via opentopodata.org).

What's real: locality names, road names, hospital counts, named
shelter candidates (schools/community halls -- the actual real-world
convention for designated flood-relief shelters in Bengaluru), and
per-zone elevation in meters.

What's estimated, and clearly labeled as such: population (derived
from OSM building count x an assumed average occupancy -- not a
census figure), elderly_pct (no public source wired in yet), and
shelter capacity (OSM has no capacity data for these buildings).

elevation_tier is not a fixed lookup -- it's computed by ranking every
seeded zone's real elevation and splitting into thirds (lowest third =
low, highest third = high). What matters for flood risk is a zone's
elevation relative to the others being modeled, not an arbitrary
absolute meter cutoff.
"""
import json
import math
import sys
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
from app.models.road import Road

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OPENTOPODATA_URL = "https://api.opentopodata.org/v1/srtm30m"
USER_AGENT = "RAHAT-seed-script/1.0 (contact: dishaagarwal023@gmail.com)"

# Avg people per residential building -- a documented estimate, not a
# real demographic figure. Revisit with real census/ward data later.
ASSUMED_OCCUPANTS_PER_BUILDING = 4
DEFAULT_SHELTER_CAPACITY = 500  # estimate -- OSM has no capacity data

ZONE_DEFS = [
    {
        "code": "Z01",
        "name": "Marathahalli",
        "geojson_file": "marathhalli.geojson",
        "center": (12.9591, 77.6974),
        "elderly_pct": 8.5,  # estimated, no real source yet
    },
    {
        "code": "Z02",
        "name": "Bellandur",
        "geojson_file": "bellanduru.geojson",
        "center": (12.9304, 77.6784),
        "elderly_pct": 7.0,  # estimated, no real source yet
    },
]


def count_buildings(geojson_path: Path) -> int:
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    return sum(1 for f in data["features"] if f["properties"].get("building"))


def fetch_real_amenities() -> list[dict]:
    """Live Overpass API query for real hospitals/schools/community
    centres within 2km of each zone center. Falls back to an empty
    list (zones just get 0 hospitals / no shelter candidates) if the
    API is unreachable, so seeding still works offline."""
    centers = [z["center"] for z in ZONE_DEFS]
    around_clauses = "\n".join(
        f'  node["amenity"~"hospital|school|community_centre"](around:2000,{lat},{lon});'
        for lat, lon in centers
    )
    query = f"""
    [out:json][timeout:25];
    (
    {around_clauses}
    );
    out body;
    """
    try:
        req = urllib.request.Request(
            OVERPASS_URL, data=query.encode("utf-8"), method="POST",
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("elements", [])
    except Exception as e:
        print(f"WARNING: Overpass API unreachable ({e}); seeding without real hospital/shelter data")
        return []


def fetch_elevations() -> dict[str, float]:
    """Live SRTM elevation lookup (opentopodata.org) for every zone's
    center, batched into one request. Falls back to 0.0 for every zone
    (flat -> all zones land in the same tier) if unreachable."""
    locations = "|".join(f"{lat},{lon}" for _, lat_lon in enumerate(z["center"] for z in ZONE_DEFS)
                          for lat, lon in [lat_lon])
    url = f"{OPENTOPODATA_URL}?locations={locations}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elevations = {}
        for zdef, result in zip(ZONE_DEFS, data["results"]):
            elevations[zdef["code"]] = result["elevation"]
        return elevations
    except Exception as e:
        print(f"WARNING: opentopodata unreachable ({e}); all zones will get elevation_m=0.0")
        return {zdef["code"]: 0.0 for zdef in ZONE_DEFS}


def classify_elevation_tiers(elevations: dict[str, float]) -> dict[str, ElevationTier]:
    """Rank zones by real elevation and split into thirds. Relative,
    not an absolute cutoff -- what matters for flood risk is how a
    zone compares to the others being modeled."""
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
        return math.hypot(lat - clat, lon - clon)

    return min(ZONE_DEFS, key=dist)["code"]


def seed() -> None:
    init_db()
    amenities = fetch_real_amenities()
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

    with Session(engine) as session:
        zones_by_code: dict[str, Zone] = {}

        for zdef in ZONE_DEFS:
            code = zdef["code"]
            existing = session.exec(select(Zone).where(Zone.code == code)).first()
            if existing:
                existing.elevation_m = round(elevations[code])
                existing.elevation_tier = elevation_tiers[code]
                session.add(existing)
                session.commit()
                session.refresh(existing)
                zones_by_code[code] = existing
                print(f"Zone {code} already exists, backfilled elevation_m={existing.elevation_m} "
                      f"tier={existing.elevation_tier.value}")
                continue

            geojson_path = DATA_DIR / zdef["geojson_file"]
            building_count = count_buildings(geojson_path)
            population_estimate = building_count * ASSUMED_OCCUPANTS_PER_BUILDING

            z = Zone(
                code=code,
                name=zdef["name"],
                population=population_estimate,
                elderly_pct=zdef["elderly_pct"],
                population_density=None,  # would need real area figures to compute properly
                elevation_tier=elevation_tiers[code],
                elevation_m=round(elevations[code]),
                hospital_count=hospital_counts[code],
                flood_risk_base=None,
            )
            session.add(z)
            session.commit()
            session.refresh(z)
            zones_by_code[code] = z
            print(f"Created zone {z.code} ({z.name}): population~{population_estimate} "
                  f"(from {building_count} buildings x {ASSUMED_OCCUPANTS_PER_BUILDING}), "
                  f"real hospital_count={z.hospital_count}, real elevation_m={z.elevation_m} "
                  f"(tier={z.elevation_tier.value})")

        # Real road, both directions, connecting the two real zones --
        # "Outer Ring Road" genuinely appears in both geojson extracts
        # and is the actual road connecting these two localities.
        marathahalli = zones_by_code["Z01"]
        bellandur = zones_by_code["Z02"]

        existing_road = session.exec(
            select(Road).where(Road.from_zone_id == marathahalli.id, Road.to_zone_id == bellandur.id)
        ).first()
        if not existing_road:
            # ~5.5km is the commonly cited distance between these two
            # localities via Outer Ring Road -- an approximate real-world
            # figure, not GPS-precise.
            session.add(Road(from_zone_id=marathahalli.id, to_zone_id=bellandur.id, capacity=None, distance_km=5.5))
            session.add(Road(from_zone_id=bellandur.id, to_zone_id=marathahalli.id, capacity=None, distance_km=5.5))
            session.commit()
            print("Created Outer Ring Road segments (Marathahalli <-> Bellandur, both directions)")
        else:
            print("Road already exists, skipping")

        # Real named schools/community centres as shelter candidates
        # (schools/halls are the actual real-world designated
        # flood-shelter convention in Bengaluru) -- capacity is still
        # an estimate, OSM has no capacity data for these buildings.
        shelter_counter = 1
        for zdef in ZONE_DEFS:
            code = zdef["code"]
            zone_ = zones_by_code[code]
            names = shelter_candidates[code][:2]  # cap at 2 per zone for a manageable demo dataset

            if not names:
                names = [f"[PLACEHOLDER] {zdef['name']} Community Shelter"]

            for name in names:
                shelter_code = f"S{shelter_counter:02d}"
                shelter_counter += 1
                existing_shelter = session.exec(select(Shelter).where(Shelter.code == shelter_code)).first()
                if existing_shelter:
                    print(f"Shelter {shelter_code} already exists, skipping")
                    continue
                session.add(Shelter(
                    code=shelter_code, name=name, zone_id=zone_.id,
                    capacity=DEFAULT_SHELTER_CAPACITY, has_medical=False,
                ))
                session.commit()
                print(f"Created shelter {shelter_code}: {name} ({zdef['name']})")


if __name__ == "__main__":
    seed()
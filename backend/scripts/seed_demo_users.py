"""
Seeds real demo accounts, each properly mapped to a real zone via
User.zone_id -- replaces the various one-off test users created by
hand during development. Looks zones up by code (not a hardcoded id),
so this works on any freshly-seeded database.

Passwords are all "demo1234" -- fine for a local dev/demo database,
never for anything real.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.db.session import engine, init_db
from app.core.roles import RoleEnum
from app.core.security import hash_secret
from app.models import (  # noqa: F401
    user, zone, shelter, road, scenario, simulation,
    sensor_event, citizen_report, risk_score, vulnerability_score, route_option,
    recommendation, approval_action, audit_event,
)
from app.models.user import User
from app.models.zone import Zone

DEMO_PASSWORD = "demo1234"

# code -> (email, name, role)
DEMO_ACCOUNTS = [
    (None, "coordinator@rahat.dev", "Demo Coordinator", RoleEnum.CENTRAL_COORDINATOR),
    ("Z01", "za.marathahalli@rahat.dev", "Marathahalli Zone Admin", RoleEnum.ZONE_ADMIN),
    ("Z02", "za.bellandur@rahat.dev", "Bellandur Zone Admin", RoleEnum.ZONE_ADMIN),
    ("Z05", "za.hsrlayout@rahat.dev", "HSR Layout Zone Admin", RoleEnum.ZONE_ADMIN),
    ("Z02", "ndrf.bellandur@rahat.dev", "Bellandur NDRF Team", RoleEnum.NDRF),
]


def seed() -> None:
    init_db()

    with Session(engine) as session:
        for code, email, name, role in DEMO_ACCOUNTS:
            existing = session.exec(select(User).where(User.email == email)).first()
            zone_id = None
            if code is not None:
                zone_ = session.exec(select(Zone).where(Zone.code == code)).first()
                if zone_ is None:
                    print(f"WARNING: zone {code} not found, skipping {email}")
                    continue
                zone_id = zone_.id

            if existing:
                existing.zone_id = zone_id
                session.add(existing)
                session.commit()
                print(f"Updated {email}: zone_id={zone_id}")
                continue

            u = User(
                email=email, name=name, role=role, zone_id=zone_id,
                hashed_secret=hash_secret(DEMO_PASSWORD),
            )
            session.add(u)
            session.commit()
            print(f"Created {email} ({role.value}), zone_id={zone_id}, password={DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()

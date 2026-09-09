"""
Shared pytest fixtures. Tests run against a real Postgres database
(rahat_test, a sibling of the dev db in the same container) rather
than mocks -- every fixture here sets up real rows and every test
exercises real service/engine code against them.

Each test gets its own transaction that's rolled back afterward, so
tests can't see each other's writes and never touch the dev database.
"""
import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://rahat:rahat@localhost:5432/rahat_test"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from datetime import datetime, timedelta, timezone

from app.core.roles import RoleEnum
from app.core.security import hash_secret
from app.db.session import get_session
from app.main import app
from app.models.zone import Zone
from app.models.shelter import Shelter
from app.models.road import Road
from app.models.user import User
from app.models.scenario import Scenario
from app.models.simulation import SimulationRun, SimulationTick
from app.models.recommendation import Recommendation
from app.core.enums import ElevationTier, RecommendationStatus, SimulationStatus

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(TEST_DATABASE_URL, echo=False)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def session():
    """A session bound to one connection/transaction. Service code
    under test can call session.commit() freely -- SQLAlchemy commits
    into a SAVEPOINT (join_transaction_mode) rather than the real
    transaction, so the final rollback here always undoes everything."""
    connection = engine.connect()
    transaction = connection.begin()
    db_session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield db_session

    db_session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(session):
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def make_zone(session):
    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        defaults = dict(
            name=f"Test Zone {counter['n']}",
            code=f"TZ{counter['n']:02d}",
            elevation_tier=ElevationTier.MID,
            population=10000,
            elderly_pct=8.0,
            population_density=5000,
            hospital_count=1,
        )
        defaults.update(overrides)
        zone = Zone(**defaults)
        session.add(zone)
        session.commit()
        session.refresh(zone)
        return zone

    return _make


@pytest.fixture()
def make_shelter(session):
    counter = {"n": 0}

    def _make(zone_id, **overrides):
        counter["n"] += 1
        defaults = dict(
            code=f"TS{counter['n']:02d}", name=f"Test Shelter {counter['n']}",
            zone_id=zone_id, capacity=500, current_occupancy=0, has_medical=False,
        )
        defaults.update(overrides)
        shelter = Shelter(**defaults)
        session.add(shelter)
        session.commit()
        session.refresh(shelter)
        return shelter

    return _make


@pytest.fixture()
def make_road(session):
    def _make(from_zone_id, to_zone_id, **overrides):
        defaults = dict(from_zone_id=from_zone_id, to_zone_id=to_zone_id, distance_km=1.0, capacity=1000)
        defaults.update(overrides)
        road = Road(**defaults)
        session.add(road)
        session.commit()
        session.refresh(road)
        return road

    return _make


@pytest.fixture()
def make_user(session):
    counter = {"n": 0}

    def _make(role: RoleEnum, password: str = "testpass123", zone_id: int | None = None, **overrides):
        counter["n"] += 1
        defaults = dict(
            email=f"test.user{counter['n']}@rahat.dev", name=f"Test User {counter['n']}",
            role=role, hashed_secret=hash_secret(password), zone_id=zone_id,
        )
        defaults.update(overrides)
        user = User(**defaults)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    return _make


@pytest.fixture()
def make_scenario(session):
    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        defaults = dict(name=f"Test Scenario {counter['n']}", scenario_type="moderate_flood", config_json={"severity": 1.0})
        defaults.update(overrides)
        scenario = Scenario(**defaults)
        session.add(scenario)
        session.commit()
        session.refresh(scenario)
        return scenario

    return _make


@pytest.fixture()
def make_run(session, make_scenario, make_user):
    def _make(**overrides):
        scenario = overrides.pop("scenario", None) or make_scenario()
        starter = overrides.pop("started_by", None) or make_user(RoleEnum.CENTRAL_COORDINATOR)
        defaults = dict(
            scenario_id=scenario.id, started_by_user_id=starter.id,
            status=SimulationStatus.RUNNING, started_at=datetime.now(timezone.utc),
        )
        defaults.update(overrides)
        run = SimulationRun(**defaults)
        session.add(run)
        session.commit()
        session.refresh(run)
        return run

    return _make


@pytest.fixture()
def make_tick(session):
    counter = {"n": 0}

    def _make(run_id, **overrides):
        defaults = dict(
            simulation_run_id=run_id, tick_number=counter["n"],
            timestamp=datetime.now(timezone.utc), raw_state_json={},
        )
        counter["n"] += 1
        defaults.update(overrides)
        tick = SimulationTick(**defaults)
        session.add(tick)
        session.commit()
        session.refresh(tick)
        return tick

    return _make


@pytest.fixture()
def make_recommendation(session):
    def _make(run_id, tick_id, zone_id, **overrides):
        defaults = dict(
            simulation_run_id=run_id, simulation_tick_id=tick_id, zone_id=zone_id,
            type="evacuation_assignment",
            payload_json={"zone_id": zone_id, "assigned_shelter_id": None, "assigned_population": 0, "reason": "test"},
            status=RecommendationStatus.PENDING_REVIEW,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        defaults.update(overrides)
        rec = Recommendation(**defaults)
        session.add(rec)
        session.commit()
        session.refresh(rec)
        return rec

    return _make


@pytest.fixture()
def auth_headers(client):
    def _headers(email: str, password: str, role: str) -> dict:
        r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _headers

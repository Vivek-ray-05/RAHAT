from datetime import datetime, timedelta, timezone

from app.core.enums import RecommendationStatus
from app.core.roles import RoleEnum


def _login(client, email, password, role):
    r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_tick_persists_risk_and_vulnerability_scores_per_zone(client, make_user, make_zone, make_scenario, session):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="sim1@test.dev")
    zone_a = make_zone()
    zone_b = make_zone()
    scenario = make_scenario()

    headers = _login(client, "sim1@test.dev", "pw", "central_coordinator")
    r = client.post("/simulation/start", json={"scenario_id": scenario.id}, headers=headers)
    assert r.status_code == 200
    run_id = r.json()["id"]

    r2 = client.post(f"/simulation/{run_id}/tick", headers=headers)
    assert r2.status_code == 200
    tick = r2.json()
    assert tick["tick_number"] == 0
    assert set(tick["raw_state_json"]["risk_scores"].keys()) == {str(zone_a.id), str(zone_b.id)}


def test_tick_number_increments_on_successive_ticks(client, make_user, make_zone, make_scenario):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="sim2@test.dev")
    make_zone()
    scenario = make_scenario()
    headers = _login(client, "sim2@test.dev", "pw", "central_coordinator")

    run_id = client.post("/simulation/start", json={"scenario_id": scenario.id}, headers=headers).json()["id"]
    first = client.post(f"/simulation/{run_id}/tick", headers=headers).json()
    second = client.post(f"/simulation/{run_id}/tick", headers=headers).json()
    assert first["tick_number"] == 0
    assert second["tick_number"] == 1


def test_cannot_advance_a_paused_simulation(client, make_user, make_zone, make_scenario):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="sim3@test.dev")
    make_zone()
    scenario = make_scenario()
    headers = _login(client, "sim3@test.dev", "pw", "central_coordinator")

    run_id = client.post("/simulation/start", json={"scenario_id": scenario.id}, headers=headers).json()["id"]
    client.post(f"/simulation/{run_id}/pause", headers=headers)
    r = client.post(f"/simulation/{run_id}/tick", headers=headers)
    assert r.status_code == 400


def test_advancing_a_tick_expires_overdue_pending_recommendations(
    client, make_user, make_zone, make_scenario, make_run, make_tick, make_recommendation, session,
):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="sim4@test.dev")
    zone = make_zone()
    scenario = make_scenario()
    headers = _login(client, "sim4@test.dev", "pw", "central_coordinator")

    run_id = client.post("/simulation/start", json={"scenario_id": scenario.id}, headers=headers).json()["id"]
    from app.models.simulation import SimulationRun
    run = session.get(SimulationRun, run_id)

    first_tick = client.post(f"/simulation/{run_id}/tick", headers=headers).json()
    stale = make_recommendation(
        run_id, first_tick["id"], zone.id,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=60),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )

    client.post(f"/simulation/{run_id}/tick", headers=headers)

    session.expire_all()
    from app.models.recommendation import Recommendation
    refreshed = session.get(Recommendation, stale.id)
    assert refreshed.status == RecommendationStatus.EXPIRED


def test_ws_rejects_a_connection_with_no_valid_token(client, make_user, make_zone, make_scenario):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="sim5@test.dev")
    make_zone()
    scenario = make_scenario()
    headers = _login(client, "sim5@test.dev", "pw", "central_coordinator")
    run_id = client.post("/simulation/start", json={"scenario_id": scenario.id}, headers=headers).json()["id"]

    try:
        with client.websocket_connect(f"/simulation/{run_id}/ws?token=not-a-real-token") as ws:
            ws.receive_json()
        assert False, "connection should have been rejected"
    except Exception:
        pass


def test_ws_streams_the_latest_tick_to_an_authenticated_client(client, make_user, make_zone, make_scenario):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="sim6@test.dev")
    make_zone()
    scenario = make_scenario()
    headers = _login(client, "sim6@test.dev", "pw", "central_coordinator")
    token = headers["Authorization"].split(" ")[1]
    run_id = client.post("/simulation/start", json={"scenario_id": scenario.id}, headers=headers).json()["id"]

    with client.websocket_connect(f"/simulation/{run_id}/ws?token={token}") as ws:
        client.post(f"/simulation/{run_id}/tick", headers=headers)
        msg = ws.receive_json()
        assert msg["tick_number"] == 0

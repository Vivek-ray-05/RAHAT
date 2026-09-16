from app.core.roles import RoleEnum


def _login(client, email, password, role):
    r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_coordinator_can_list_scenarios(client, make_user, make_scenario):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="scenlist@test.dev")
    make_scenario(name="Test Scenario A")
    make_scenario(name="Test Scenario B")

    headers = _login(client, "scenlist@test.dev", "pw", "central_coordinator")
    r = client.get("/scenarios", headers=headers)

    assert r.status_code == 200
    names = {s["name"] for s in r.json()}
    assert {"Test Scenario A", "Test Scenario B"} <= names


def test_zone_admin_cannot_list_scenarios(client, make_user):
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="scenzone@test.dev")

    headers = _login(client, "scenzone@test.dev", "pw", "zone_admin")
    r = client.get("/scenarios", headers=headers)

    assert r.status_code == 403


def test_coordinator_can_list_simulation_runs_newest_first(client, make_user, make_run):
    coordinator = make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="runlist@test.dev")
    older = make_run(started_by=coordinator)
    newer = make_run(started_by=coordinator)

    headers = _login(client, "runlist@test.dev", "pw", "central_coordinator")
    r = client.get("/simulation", headers=headers)

    assert r.status_code == 200
    ids = [row["id"] for row in r.json()]
    assert ids.index(newer.id) < ids.index(older.id)
    top = next(row for row in r.json() if row["id"] == newer.id)
    assert top["started_by_name"] == coordinator.name
    assert top["scenario_name"]
    assert top["tick_count"] == 0


def test_run_list_reports_the_real_tick_count(client, make_user, make_run, make_tick):
    coordinator = make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="runticks@test.dev")
    run = make_run(started_by=coordinator)
    make_tick(run.id)
    make_tick(run.id)
    make_tick(run.id)

    headers = _login(client, "runticks@test.dev", "pw", "central_coordinator")
    r = client.get("/simulation", headers=headers)

    row = next(row for row in r.json() if row["id"] == run.id)
    assert row["tick_count"] == 3


def test_zone_admin_cannot_list_simulation_runs(client, make_user):
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="runzone@test.dev")

    headers = _login(client, "runzone@test.dev", "pw", "zone_admin")
    r = client.get("/simulation", headers=headers)

    assert r.status_code == 403

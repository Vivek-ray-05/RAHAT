from app.core.enums import RouteStatus
from app.core.roles import RoleEnum
from app.models.route_option import RouteOption


def _login(client, email, password, role):
    r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_lists_the_latest_route_per_zone_for_a_run(
    session, client, make_user, make_zone, make_shelter, make_run, make_tick,
):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="routes1@test.dev")
    zone = make_zone()
    shelter = make_shelter(zone.id)
    run = make_run()
    older_tick = make_tick(run.id)
    newer_tick = make_tick(run.id)

    session.add(RouteOption(
        simulation_tick_id=older_tick.id, from_zone_id=zone.id, to_shelter_id=shelter.id,
        path_json={"path": ["old"]}, eta=10.0, status=RouteStatus.USABLE,
    ))
    session.add(RouteOption(
        simulation_tick_id=newer_tick.id, from_zone_id=zone.id, to_shelter_id=shelter.id,
        path_json={"path": ["new"]}, eta=5.0, status=RouteStatus.USABLE,
    ))
    session.commit()

    headers = _login(client, "routes1@test.dev", "pw", "central_coordinator")
    r = client.get(f"/routes?simulation_run_id={run.id}", headers=headers)

    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["path_json"] == {"path": ["new"]}


def test_defaults_to_the_most_recently_started_run(
    session, client, make_user, make_zone, make_shelter, make_run, make_tick,
):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="routes2@test.dev")
    zone = make_zone()
    shelter = make_shelter(zone.id)
    make_run()  # an older run with no routes
    newest_run = make_run()
    tick = make_tick(newest_run.id)
    session.add(RouteOption(
        simulation_tick_id=tick.id, from_zone_id=zone.id, to_shelter_id=shelter.id,
        path_json={"path": []}, eta=1.0, status=RouteStatus.USABLE,
    ))
    session.commit()

    headers = _login(client, "routes2@test.dev", "pw", "central_coordinator")
    r = client.get("/routes", headers=headers)

    assert r.status_code == 200
    assert len(r.json()) == 1


def test_citizen_cannot_list_routes(client, make_user):
    make_user(RoleEnum.CITIZEN, password="pw", email="routes3@test.dev")

    headers = _login(client, "routes3@test.dev", "pw", "citizen")
    r = client.get("/routes", headers=headers)

    assert r.status_code == 403

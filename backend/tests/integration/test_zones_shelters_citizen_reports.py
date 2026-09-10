from app.core.roles import RoleEnum


def _login(client, email, password, role):
    r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_zone_response_carries_data_quality_json(client, make_user, make_zone):
    make_zone(
        name="Provenance Zone",
        data_quality_json={"population": {"quality": "estimated", "note": "test note"}},
    )
    make_user(RoleEnum.CITIZEN, password="pw", email="dq1@test.dev")
    headers = _login(client, "dq1@test.dev", "pw", "citizen")

    r = client.get("/zones", headers=headers)
    zone = next(z for z in r.json() if z["name"] == "Provenance Zone")
    assert zone["data_quality_json"]["population"]["quality"] == "estimated"


def test_zone_defaults_to_empty_data_quality_json(client, make_user, make_zone):
    make_zone(name="No Provenance Zone")
    make_user(RoleEnum.CITIZEN, password="pw", email="dq2@test.dev")
    headers = _login(client, "dq2@test.dev", "pw", "citizen")

    r = client.get("/zones", headers=headers)
    zone = next(z for z in r.json() if z["name"] == "No Provenance Zone")
    assert zone["data_quality_json"] == {}


def test_list_zones_returns_real_seeded_zones(client, make_user, make_zone):
    make_zone(name="Alpha")
    make_zone(name="Beta")
    make_user(RoleEnum.CITIZEN, password="pw", email="z1@test.dev")
    headers = _login(client, "z1@test.dev", "pw", "citizen")

    r = client.get("/zones", headers=headers)
    assert r.status_code == 200
    names = {z["name"] for z in r.json()}
    assert {"Alpha", "Beta"}.issubset(names)


def test_shelters_can_be_filtered_by_zone(client, make_user, make_zone, make_shelter):
    zone_a, zone_b = make_zone(), make_zone()
    make_shelter(zone_a.id, name="Shelter A")
    make_shelter(zone_b.id, name="Shelter B")
    make_user(RoleEnum.CITIZEN, password="pw", email="s1@test.dev")
    headers = _login(client, "s1@test.dev", "pw", "citizen")

    r = client.get("/shelters", params={"zone_id": zone_a.id}, headers=headers)
    assert r.status_code == 200
    names = {s["name"] for s in r.json()}
    assert names == {"Shelter A"}


def test_zone_with_no_route_yet_returns_404(client, make_user, make_zone):
    zone = make_zone()
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="z2@test.dev")
    headers = _login(client, "z2@test.dev", "pw", "central_coordinator")

    r = client.get(f"/zones/{zone.id}/routes", headers=headers)
    assert r.status_code == 404


def test_citizen_cannot_read_a_zones_route(client, make_user, make_zone):
    zone = make_zone()
    make_user(RoleEnum.CITIZEN, password="pw", email="z3@test.dev")
    headers = _login(client, "z3@test.dev", "pw", "citizen")

    r = client.get(f"/zones/{zone.id}/routes", headers=headers)
    assert r.status_code == 403


def test_ndrf_can_read_a_zones_route(client, make_user, make_zone):
    zone = make_zone()
    make_user(RoleEnum.NDRF, password="pw", email="z4@test.dev")
    headers = _login(client, "z4@test.dev", "pw", "ndrf")

    r = client.get(f"/zones/{zone.id}/routes", headers=headers)
    assert r.status_code == 404  # no route computed yet, but not blocked by role


def test_citizen_can_submit_a_report_and_it_is_attributed_to_them(client, make_user, make_zone):
    zone = make_zone()
    citizen = make_user(RoleEnum.CITIZEN, password="pw", email="c1@test.dev")
    headers = _login(client, "c1@test.dev", "pw", "citizen")

    r = client.post("/citizen-reports", json={"zone_id": zone.id, "description": "Water rising fast"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == citizen.id
    assert body["status"] == "new"


def test_citizen_reports_can_be_filtered_by_zone(client, make_user, make_zone):
    zone_a, zone_b = make_zone(), make_zone()
    make_user(RoleEnum.CITIZEN, password="pw", email="c2@test.dev")
    headers = _login(client, "c2@test.dev", "pw", "citizen")

    client.post("/citizen-reports", json={"zone_id": zone_a.id, "description": "report A"}, headers=headers)
    client.post("/citizen-reports", json={"zone_id": zone_b.id, "description": "report B"}, headers=headers)

    r = client.get("/citizen-reports", params={"zone_id": zone_a.id}, headers=headers)
    descriptions = {rep["description"] for rep in r.json()}
    assert descriptions == {"report A"}

from app.core.roles import RoleEnum


def _login(client, email, password, role):
    r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_ndrf_can_block_a_road(client, make_user, make_zone, make_road):
    zone_a, zone_b = make_zone(), make_zone()
    road = make_road(zone_a.id, zone_b.id)
    make_user(RoleEnum.NDRF, password="pw", email="ndrf1@test.dev")
    headers = _login(client, "ndrf1@test.dev", "pw", "ndrf")

    r = client.post(f"/roads/{road.id}/block", json={"reason": "debris"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["road_id"] == road.id
    assert body["reason"] == "debris"


def test_blocking_a_road_persists_is_blocked_and_blocked_by(client, make_user, make_zone, make_road):
    zone_a, zone_b = make_zone(), make_zone()
    road = make_road(zone_a.id, zone_b.id)
    admin = make_user(RoleEnum.ZONE_ADMIN, password="pw", email="za_block@test.dev", zone_id=zone_a.id)
    headers = _login(client, "za_block@test.dev", "pw", "zone_admin")

    client.post(f"/roads/{road.id}/block", json={}, headers=headers)

    roads = client.get("/roads", headers=headers).json()
    updated = next(r for r in roads if r["id"] == road.id)
    assert updated["is_blocked"] is True
    assert updated["blocked_by_user_id"] == admin.id


def test_citizen_cannot_block_a_road(client, make_user, make_zone, make_road):
    zone_a, zone_b = make_zone(), make_zone()
    road = make_road(zone_a.id, zone_b.id)
    make_user(RoleEnum.CITIZEN, password="pw", email="citizen_block@test.dev")
    headers = _login(client, "citizen_block@test.dev", "pw", "citizen")

    r = client.post(f"/roads/{road.id}/block", json={}, headers=headers)
    assert r.status_code == 403


def test_blocking_an_unknown_road_is_404(client, make_user):
    make_user(RoleEnum.NDRF, password="pw", email="ndrf2@test.dev")
    headers = _login(client, "ndrf2@test.dev", "pw", "ndrf")
    r = client.post("/roads/999999/block", json={}, headers=headers)
    assert r.status_code == 404


def test_citizen_cannot_list_roads(client, make_user):
    make_user(RoleEnum.CITIZEN, password="pw", email="citizen_list_roads@test.dev")
    headers = _login(client, "citizen_list_roads@test.dev", "pw", "citizen")
    r = client.get("/roads", headers=headers)
    assert r.status_code == 403


def test_coordinator_can_list_roads(client, make_user, make_zone, make_road):
    zone_a, zone_b = make_zone(), make_zone()
    make_road(zone_a.id, zone_b.id)
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="coord_list_roads@test.dev")
    headers = _login(client, "coord_list_roads@test.dev", "pw", "central_coordinator")
    r = client.get("/roads", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1

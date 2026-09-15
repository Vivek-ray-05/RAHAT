from app.core.roles import RoleEnum


def _login(client, email, password, role):
    r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_zone_admin_can_update_their_own_zones_shelter_occupancy(client, make_user, make_zone, make_shelter):
    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=500, current_occupancy=100)
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="occ1@test.dev", zone_id=zone.id)

    headers = _login(client, "occ1@test.dev", "pw", "zone_admin")
    r = client.patch(f"/shelters/{shelter.id}", json={"current_occupancy": 250}, headers=headers)

    assert r.status_code == 200
    assert r.json()["current_occupancy"] == 250


def test_zone_admin_cannot_update_another_zones_shelter(client, make_user, make_zone, make_shelter):
    own_zone = make_zone()
    other_zone = make_zone()
    shelter = make_shelter(other_zone.id, capacity=500, current_occupancy=0)
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="occ2@test.dev", zone_id=own_zone.id)

    headers = _login(client, "occ2@test.dev", "pw", "zone_admin")
    r = client.patch(f"/shelters/{shelter.id}", json={"current_occupancy": 100}, headers=headers)

    assert r.status_code == 403


def test_coordinator_can_update_any_shelter(client, make_user, make_zone, make_shelter):
    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=500, current_occupancy=0)
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="occ3@test.dev")

    headers = _login(client, "occ3@test.dev", "pw", "central_coordinator")
    r = client.patch(f"/shelters/{shelter.id}", json={"current_occupancy": 300}, headers=headers)

    assert r.status_code == 200


def test_ndrf_cannot_update_shelter_occupancy(client, make_user, make_zone, make_shelter):
    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=500, current_occupancy=0)
    make_user(RoleEnum.NDRF, password="pw", email="occ4@test.dev")

    headers = _login(client, "occ4@test.dev", "pw", "ndrf")
    r = client.patch(f"/shelters/{shelter.id}", json={"current_occupancy": 10}, headers=headers)

    assert r.status_code == 403


def test_rejects_occupancy_above_capacity(client, make_user, make_zone, make_shelter):
    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=100, current_occupancy=0)
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="occ5@test.dev", zone_id=zone.id)

    headers = _login(client, "occ5@test.dev", "pw", "zone_admin")
    r = client.patch(f"/shelters/{shelter.id}", json={"current_occupancy": 150}, headers=headers)

    assert r.status_code == 400


def test_rejects_negative_occupancy(client, make_user, make_zone, make_shelter):
    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=100, current_occupancy=50)
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="occ6@test.dev", zone_id=zone.id)

    headers = _login(client, "occ6@test.dev", "pw", "zone_admin")
    r = client.patch(f"/shelters/{shelter.id}", json={"current_occupancy": -1}, headers=headers)

    assert r.status_code == 400


def test_updating_occupancy_writes_an_audit_event(session, client, make_user, make_zone, make_shelter):
    from sqlmodel import select
    from app.models.audit_event import AuditEvent

    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=500, current_occupancy=10)
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="occ7@test.dev", zone_id=zone.id)

    headers = _login(client, "occ7@test.dev", "pw", "zone_admin")
    r = client.patch(f"/shelters/{shelter.id}", json={"current_occupancy": 80}, headers=headers)
    assert r.status_code == 200

    events = session.exec(
        select(AuditEvent).where(AuditEvent.entity_type == "shelter", AuditEvent.entity_id == shelter.id)
    ).all()
    assert len(events) == 1
    assert events[0].event_type == "shelter_occupancy_updated"
    assert events[0].before_json == {"current_occupancy": 10}
    assert events[0].after_json == {"current_occupancy": 80}

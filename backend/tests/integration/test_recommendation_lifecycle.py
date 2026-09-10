from app.core.roles import RoleEnum


def _login(client, email, password, role):
    r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_approve_executes_and_updates_shelter_occupancy(client, make_user, make_zone, make_shelter, make_run, make_tick, make_recommendation):
    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=500, current_occupancy=0)
    admin = make_user(RoleEnum.ZONE_ADMIN, password="pw", email="approve@test.dev", zone_id=zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(
        run.id, tick.id, zone.id,
        payload_json={"zone_id": zone.id, "assigned_shelter_id": shelter.id, "assigned_population": 150, "reason": "test"},
    )

    headers = _login(client, "approve@test.dev", "pw", "zone_admin")
    r = client.post(f"/recommendations/{rec.id}/approve", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "executed"

    shelters_after = client.get("/shelters", headers=headers).json()
    updated = next(s for s in shelters_after if s["id"] == shelter.id)
    assert updated["current_occupancy"] == 150


def test_approve_twice_is_rejected(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    zone = make_zone()
    admin = make_user(RoleEnum.ZONE_ADMIN, password="pw", email="twice@test.dev", zone_id=zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id)

    headers = _login(client, "twice@test.dev", "pw", "zone_admin")
    first = client.post(f"/recommendations/{rec.id}/approve", headers=headers)
    assert first.status_code == 200
    second = client.post(f"/recommendations/{rec.id}/approve", headers=headers)
    assert second.status_code == 400


def test_modify_executes_with_the_modified_payload(client, make_user, make_zone, make_shelter, make_run, make_tick, make_recommendation):
    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=500, current_occupancy=0)
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="modify@test.dev", zone_id=zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id)

    headers = _login(client, "modify@test.dev", "pw", "zone_admin")
    r = client.post(
        f"/recommendations/{rec.id}/modify",
        json={"modified_payload": {"assigned_shelter_id": shelter.id, "assigned_population": 75}, "reason": "reassigned"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "executed"

    shelters_after = client.get("/shelters", headers=headers).json()
    updated = next(s for s in shelters_after if s["id"] == shelter.id)
    assert updated["current_occupancy"] == 75


def test_reject_does_not_change_shelter_state(client, make_user, make_zone, make_shelter, make_run, make_tick, make_recommendation):
    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=500, current_occupancy=0)
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="reject@test.dev", zone_id=zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(
        run.id, tick.id, zone.id,
        payload_json={"zone_id": zone.id, "assigned_shelter_id": shelter.id, "assigned_population": 100, "reason": "test"},
    )

    headers = _login(client, "reject@test.dev", "pw", "zone_admin")
    r = client.post(f"/recommendations/{rec.id}/reject", json={"reason": "not warranted"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    shelters_after = client.get("/shelters", headers=headers).json()
    updated = next(s for s in shelters_after if s["id"] == shelter.id)
    assert updated["current_occupancy"] == 0


def test_citizen_cannot_approve_a_recommendation(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    zone = make_zone()
    make_user(RoleEnum.CITIZEN, password="pw", email="citizen@test.dev")
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id)

    headers = _login(client, "citizen@test.dev", "pw", "citizen")
    r = client.post(f"/recommendations/{rec.id}/approve", headers=headers)
    assert r.status_code == 403


def test_zone_admin_only_sees_their_own_zones_pending_recommendations(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    zone_a = make_zone()
    zone_b = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="scoped@test.dev", zone_id=zone_a.id)
    run = make_run()
    tick = make_tick(run.id)
    make_recommendation(run.id, tick.id, zone_a.id)
    make_recommendation(run.id, tick.id, zone_b.id)

    headers = _login(client, "scoped@test.dev", "pw", "zone_admin")
    r = client.get("/recommendations", headers=headers)
    assert r.status_code == 200
    zone_ids = {rec["zone_id"] for rec in r.json()}
    assert zone_ids == {zone_a.id}


def test_coordinator_sees_pending_recommendations_across_all_zones(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    zone_a = make_zone()
    zone_b = make_zone()
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="coord@test.dev")
    run = make_run()
    tick = make_tick(run.id)
    make_recommendation(run.id, tick.id, zone_a.id)
    make_recommendation(run.id, tick.id, zone_b.id)

    headers = _login(client, "coord@test.dev", "pw", "central_coordinator")
    r = client.get("/recommendations", headers=headers)
    zone_ids = {rec["zone_id"] for rec in r.json()}
    assert zone_ids == {zone_a.id, zone_b.id}


def test_zone_admin_cannot_approve_another_zones_recommendation(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    own_zone = make_zone()
    other_zone = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="cross1@test.dev", zone_id=own_zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, other_zone.id)

    headers = _login(client, "cross1@test.dev", "pw", "zone_admin")
    r = client.post(f"/recommendations/{rec.id}/approve", headers=headers)
    assert r.status_code == 403


def test_zone_admin_cannot_modify_another_zones_recommendation(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    own_zone = make_zone()
    other_zone = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="cross2@test.dev", zone_id=own_zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, other_zone.id)

    headers = _login(client, "cross2@test.dev", "pw", "zone_admin")
    r = client.post(
        f"/recommendations/{rec.id}/modify",
        json={"modified_payload": {"assigned_shelter_id": None, "assigned_population": 0}},
        headers=headers,
    )
    assert r.status_code == 403


def test_zone_admin_cannot_reject_another_zones_recommendation(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    own_zone = make_zone()
    other_zone = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="cross3@test.dev", zone_id=own_zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, other_zone.id)

    headers = _login(client, "cross3@test.dev", "pw", "zone_admin")
    r = client.post(f"/recommendations/{rec.id}/reject", json={"reason": "not mine"}, headers=headers)
    assert r.status_code == 403


def test_zone_admin_can_still_approve_their_own_zones_recommendation(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    zone = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="own1@test.dev", zone_id=zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id)

    headers = _login(client, "own1@test.dev", "pw", "zone_admin")
    r = client.post(f"/recommendations/{rec.id}/approve", headers=headers)
    assert r.status_code == 200


def test_coordinator_can_approve_any_zones_recommendation(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    zone = make_zone()
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="coordapprove@test.dev")
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id)

    headers = _login(client, "coordapprove@test.dev", "pw", "central_coordinator")
    r = client.post(f"/recommendations/{rec.id}/approve", headers=headers)
    assert r.status_code == 200


def test_modify_clamps_assigned_population_to_remaining_shelter_capacity(
    client, make_user, make_zone, make_shelter, make_run, make_tick, make_recommendation,
):
    zone = make_zone()
    shelter = make_shelter(zone.id, capacity=500, current_occupancy=450)
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="clamp@test.dev", zone_id=zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id)

    headers = _login(client, "clamp@test.dev", "pw", "zone_admin")
    r = client.post(
        f"/recommendations/{rec.id}/modify",
        json={"modified_payload": {"assigned_shelter_id": shelter.id, "assigned_population": 10000}},
        headers=headers,
    )
    assert r.status_code == 200

    shelters_after = client.get("/shelters", headers=headers).json()
    updated = next(s for s in shelters_after if s["id"] == shelter.id)
    assert updated["current_occupancy"] == 500  # clamped to capacity, not 10450


def test_creating_a_recommendation_notifies_that_zones_admin(session, make_user, make_zone, make_run, make_tick):
    from sqlmodel import select
    from app.models.notification import Notification
    from app.services import recommendation_service

    zone = make_zone(name="Notify Test Zone")
    admin = make_user(RoleEnum.ZONE_ADMIN, password="pw", email="notifyme@test.dev", zone_id=zone.id)
    run = make_run()
    tick = make_tick(run.id)

    plan = {
        "evacuation_sequence": [
            {"zone_id": zone.id, "zone_name": zone.name, "reason": "High risk", "assigned_shelter_id": None, "assigned_population": 0},
        ]
    }
    recommendation_service.create_from_plan(session, run.id, tick.id, plan)

    notifications = session.exec(select(Notification).where(Notification.user_id == admin.id)).all()
    assert len(notifications) == 1
    assert "Notify Test Zone" in notifications[0].subject


def test_creating_a_recommendation_does_not_notify_a_different_zones_admin(session, make_user, make_zone, make_run, make_tick):
    from sqlmodel import select
    from app.models.notification import Notification
    from app.services import recommendation_service

    target_zone = make_zone()
    other_zone = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="notme@test.dev", zone_id=other_zone.id)
    run = make_run()
    tick = make_tick(run.id)

    plan = {
        "evacuation_sequence": [
            {"zone_id": target_zone.id, "zone_name": target_zone.name, "reason": "x", "assigned_shelter_id": None, "assigned_population": 0},
        ]
    }
    recommendation_service.create_from_plan(session, run.id, tick.id, plan)

    notifications = session.exec(select(Notification)).all()
    assert len(notifications) == 0


def test_zone_admin_cannot_read_another_zones_recommendation_by_id(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    own_zone = make_zone()
    other_zone = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="readother@test.dev", zone_id=own_zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, other_zone.id)

    headers = _login(client, "readother@test.dev", "pw", "zone_admin")
    r = client.get(f"/recommendations/{rec.id}", headers=headers)
    assert r.status_code == 403


def test_zone_admin_can_read_their_own_zones_recommendation_by_id(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    zone = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="readown@test.dev", zone_id=zone.id)
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id)

    headers = _login(client, "readown@test.dev", "pw", "zone_admin")
    r = client.get(f"/recommendations/{rec.id}", headers=headers)
    assert r.status_code == 200


def test_coordinator_can_read_any_zones_recommendation_by_id(client, make_user, make_zone, make_run, make_tick, make_recommendation):
    zone = make_zone()
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="readcoord@test.dev")
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id)

    headers = _login(client, "readcoord@test.dev", "pw", "central_coordinator")
    r = client.get(f"/recommendations/{rec.id}", headers=headers)
    assert r.status_code == 200

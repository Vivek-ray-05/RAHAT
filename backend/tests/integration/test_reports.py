from app.core.roles import RoleEnum


def _login(client, email, password, role):
    r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_report_includes_scenario_run_and_tick_summary(client, make_user, make_zone, make_run, make_tick):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="coord1@test.dev")
    run = make_run()
    make_tick(run.id)
    make_tick(run.id)

    headers = _login(client, "coord1@test.dev", "pw", "central_coordinator")
    r = client.get(f"/reports/{run.id}", headers=headers)

    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == run.id
    assert body["tick_count"] == 2
    assert body["status"] == "running"


def test_report_includes_a_reviewed_recommendation(
    client, make_user, make_zone, make_run, make_tick, make_recommendation,
):
    zone = make_zone(name="Report Test Zone")
    admin = make_user(RoleEnum.ZONE_ADMIN, password="pw", email="reportadmin@test.dev", zone_id=zone.id)
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="coord2@test.dev")
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id, payload_json={"reason": "Rising water level"})

    admin_headers = _login(client, "reportadmin@test.dev", "pw", "zone_admin")
    approve = client.post(f"/recommendations/{rec.id}/approve", headers=admin_headers)
    assert approve.status_code == 200

    coord_headers = _login(client, "coord2@test.dev", "pw", "central_coordinator")
    r = client.get(f"/reports/{run.id}", headers=coord_headers)

    assert r.status_code == 200
    recs = r.json()["recommendations"]
    assert len(recs) == 1
    assert recs[0]["zone_name"] == "Report Test Zone"
    assert recs[0]["reason"] == "Rising water level"
    assert recs[0]["status"] == "executed"
    assert recs[0]["review"]["action"] == "approve"
    assert recs[0]["review"]["reviewed_by_name"] == admin.name
    assert r.json()["status_counts"] == {"executed": 1}


def test_report_includes_the_audit_trail_for_its_recommendations(
    client, make_user, make_zone, make_run, make_tick, make_recommendation,
):
    zone = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="reportaudit@test.dev", zone_id=zone.id)
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="coord3@test.dev")
    run = make_run()
    tick = make_tick(run.id)
    rec = make_recommendation(run.id, tick.id, zone.id)

    admin_headers = _login(client, "reportaudit@test.dev", "pw", "zone_admin")
    client.post(f"/recommendations/{rec.id}/reject", json={"reason": "no longer needed"}, headers=admin_headers)

    coord_headers = _login(client, "coord3@test.dev", "pw", "central_coordinator")
    r = client.get(f"/reports/{run.id}", headers=coord_headers)

    events = r.json()["audit_trail"]
    assert len(events) == 1
    assert events[0]["event_type"] == "recommendation_rejected"
    assert events[0]["entity_id"] == rec.id


def test_zone_admin_report_is_scoped_to_their_own_zone(
    client, make_user, make_zone, make_run, make_tick, make_recommendation,
):
    zone_a = make_zone()
    zone_b = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="pw", email="scopedreport@test.dev", zone_id=zone_a.id)
    run = make_run()
    tick = make_tick(run.id)
    make_recommendation(run.id, tick.id, zone_a.id)
    make_recommendation(run.id, tick.id, zone_b.id)

    headers = _login(client, "scopedreport@test.dev", "pw", "zone_admin")
    r = client.get(f"/reports/{run.id}", headers=headers)

    assert r.status_code == 200
    zone_ids = {rec["zone_id"] for rec in r.json()["recommendations"]}
    assert zone_ids == {zone_a.id}


def test_coordinator_report_sees_recommendations_across_all_zones(
    client, make_user, make_zone, make_run, make_tick, make_recommendation,
):
    zone_a = make_zone()
    zone_b = make_zone()
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="coord4@test.dev")
    run = make_run()
    tick = make_tick(run.id)
    make_recommendation(run.id, tick.id, zone_a.id)
    make_recommendation(run.id, tick.id, zone_b.id)

    headers = _login(client, "coord4@test.dev", "pw", "central_coordinator")
    r = client.get(f"/reports/{run.id}", headers=headers)

    zone_ids = {rec["zone_id"] for rec in r.json()["recommendations"]}
    assert zone_ids == {zone_a.id, zone_b.id}


def test_citizen_cannot_read_a_report(client, make_user, make_run):
    make_user(RoleEnum.CITIZEN, password="pw", email="reportcitizen@test.dev")
    run = make_run()

    headers = _login(client, "reportcitizen@test.dev", "pw", "citizen")
    r = client.get(f"/reports/{run.id}", headers=headers)

    assert r.status_code == 403


def test_ndrf_can_read_a_report(client, make_user, make_run):
    make_user(RoleEnum.NDRF, password="pw", email="reportndrf@test.dev")
    run = make_run()

    headers = _login(client, "reportndrf@test.dev", "pw", "ndrf")
    r = client.get(f"/reports/{run.id}", headers=headers)

    assert r.status_code == 200


def test_report_for_a_missing_run_is_404(client, make_user):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="coord5@test.dev")

    headers = _login(client, "coord5@test.dev", "pw", "central_coordinator")
    r = client.get("/reports/999999", headers=headers)

    assert r.status_code == 404

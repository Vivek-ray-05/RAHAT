from app.core.roles import RoleEnum


def _login(client, email, password, role):
    r = client.post("/auth/login", json={"email": email, "password": password, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# Real-shaped Bengaluru coordinates, just distinct enough to have a
# clear nearest/farthest ordering for the test.
ZONE_COORDS = (12.9591, 77.6974)
NEAR_SHELTER_COORDS = (12.9600, 77.6980)
FAR_SHELTER_COORDS = (13.1007, 77.5963)


def test_returns_the_nearest_shelter_with_room_when_no_active_recommendation(
    client, make_user, make_zone, make_shelter,
):
    make_user(RoleEnum.CITIZEN, password="pw", email="near1@test.dev")
    zone = make_zone(center_lat=ZONE_COORDS[0], center_lon=ZONE_COORDS[1])
    near = make_shelter(zone.id, lat=NEAR_SHELTER_COORDS[0], lon=NEAR_SHELTER_COORDS[1], capacity=500, current_occupancy=0)
    make_shelter(zone.id, lat=FAR_SHELTER_COORDS[0], lon=FAR_SHELTER_COORDS[1], capacity=500, current_occupancy=0)

    headers = _login(client, "near1@test.dev", "pw", "citizen")
    r = client.get(f"/shelters/nearest?zone_id={zone.id}", headers=headers)

    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "nearest_available"
    assert body["shelter"]["id"] == near.id
    assert body["distance_km"] < 5


def test_skips_a_full_shelter_in_favor_of_one_with_room(client, make_user, make_zone, make_shelter):
    make_user(RoleEnum.CITIZEN, password="pw", email="near2@test.dev")
    zone = make_zone(center_lat=ZONE_COORDS[0], center_lon=ZONE_COORDS[1])
    make_shelter(zone.id, lat=NEAR_SHELTER_COORDS[0], lon=NEAR_SHELTER_COORDS[1], capacity=100, current_occupancy=100)
    far_with_room = make_shelter(zone.id, lat=FAR_SHELTER_COORDS[0], lon=FAR_SHELTER_COORDS[1], capacity=100, current_occupancy=0)

    headers = _login(client, "near2@test.dev", "pw", "citizen")
    r = client.get(f"/shelters/nearest?zone_id={zone.id}", headers=headers)

    assert r.status_code == 200
    assert r.json()["shelter"]["id"] == far_with_room.id


def test_prefers_an_official_active_recommendation_over_distance(
    client, make_user, make_zone, make_shelter, make_run, make_tick, make_recommendation,
):
    make_user(RoleEnum.CITIZEN, password="pw", email="near3@test.dev")
    zone = make_zone(center_lat=ZONE_COORDS[0], center_lon=ZONE_COORDS[1])
    make_shelter(zone.id, lat=NEAR_SHELTER_COORDS[0], lon=NEAR_SHELTER_COORDS[1], capacity=500, current_occupancy=0)
    official = make_shelter(zone.id, lat=FAR_SHELTER_COORDS[0], lon=FAR_SHELTER_COORDS[1], capacity=500, current_occupancy=0)
    run = make_run()
    tick = make_tick(run.id)
    make_recommendation(
        run.id, tick.id, zone.id,
        payload_json={"zone_id": zone.id, "assigned_shelter_id": official.id, "assigned_population": 100, "reason": "test"},
    )

    headers = _login(client, "near3@test.dev", "pw", "citizen")
    r = client.get(f"/shelters/nearest?zone_id={zone.id}", headers=headers)

    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "official_recommendation"
    assert body["shelter"]["id"] == official.id


def test_ignores_a_rejected_recommendation(
    client, make_user, make_zone, make_shelter, make_run, make_tick, make_recommendation,
):
    from app.core.enums import RecommendationStatus

    make_user(RoleEnum.CITIZEN, password="pw", email="near4@test.dev")
    zone = make_zone(center_lat=ZONE_COORDS[0], center_lon=ZONE_COORDS[1])
    near = make_shelter(zone.id, lat=NEAR_SHELTER_COORDS[0], lon=NEAR_SHELTER_COORDS[1], capacity=500, current_occupancy=0)
    rejected_shelter = make_shelter(zone.id, lat=FAR_SHELTER_COORDS[0], lon=FAR_SHELTER_COORDS[1], capacity=500, current_occupancy=0)
    run = make_run()
    tick = make_tick(run.id)
    make_recommendation(
        run.id, tick.id, zone.id,
        status=RecommendationStatus.REJECTED,
        payload_json={"zone_id": zone.id, "assigned_shelter_id": rejected_shelter.id, "assigned_population": 0, "reason": "test"},
    )

    headers = _login(client, "near4@test.dev", "pw", "citizen")
    r = client.get(f"/shelters/nearest?zone_id={zone.id}", headers=headers)

    assert r.status_code == 200
    assert r.json()["source"] == "nearest_available"
    assert r.json()["shelter"]["id"] == near.id


def test_404_when_no_shelter_has_room(client, make_user, make_zone, make_shelter):
    make_user(RoleEnum.CITIZEN, password="pw", email="near5@test.dev")
    zone = make_zone(center_lat=ZONE_COORDS[0], center_lon=ZONE_COORDS[1])
    make_shelter(zone.id, lat=NEAR_SHELTER_COORDS[0], lon=NEAR_SHELTER_COORDS[1], capacity=10, current_occupancy=10)

    headers = _login(client, "near5@test.dev", "pw", "citizen")
    r = client.get(f"/shelters/nearest?zone_id={zone.id}", headers=headers)

    assert r.status_code == 404

from app.core.roles import RoleEnum


def test_password_login_succeeds_with_correct_credentials(client, make_user):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="correct-horse", email="coord@test.dev")
    r = client.post("/auth/login", json={"email": "coord@test.dev", "password": "correct-horse", "role": "central_coordinator"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "central_coordinator"
    assert "access_token" in body


def test_password_login_fails_with_wrong_password(client, make_user):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="correct-horse", email="coord2@test.dev")
    r = client.post("/auth/login", json={"email": "coord2@test.dev", "password": "wrong", "role": "central_coordinator"})
    assert r.status_code == 401


def test_password_login_fails_when_role_does_not_match_account(client, make_user):
    make_user(RoleEnum.ZONE_ADMIN, password="correct-horse", email="za@test.dev")
    r = client.post("/auth/login", json={"email": "za@test.dev", "password": "correct-horse", "role": "central_coordinator"})
    assert r.status_code == 401


def test_login_response_carries_zone_id_for_zone_scoped_roles(client, make_user, make_zone):
    zone = make_zone()
    make_user(RoleEnum.ZONE_ADMIN, password="correct-horse", email="za2@test.dev", zone_id=zone.id)
    r = client.post("/auth/login", json={"email": "za2@test.dev", "password": "correct-horse", "role": "zone_admin"})
    assert r.json()["zone_id"] == zone.id


def test_login_response_has_no_zone_id_for_coordinator(client, make_user):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="correct-horse", email="coord3@test.dev")
    r = client.post("/auth/login", json={"email": "coord3@test.dev", "password": "correct-horse", "role": "central_coordinator"})
    assert r.json()["zone_id"] is None


def test_otp_login_creates_a_new_citizen_on_first_use(client):
    r = client.post("/auth/otp/request", json={"phone": "9998887777"})
    assert r.status_code == 200
    otp = r.json()["dev_otp"]

    r2 = client.post("/auth/otp/verify", json={"phone": "9998887777", "code": otp})
    assert r2.status_code == 200
    assert r2.json()["role"] == "citizen"


def test_otp_verify_fails_with_wrong_code(client):
    client.post("/auth/otp/request", json={"phone": "9997776666"})
    r = client.post("/auth/otp/verify", json={"phone": "9997776666", "code": "000000"})
    assert r.status_code == 401


def test_otp_is_stored_in_redis_with_a_ttl(client):
    """The OTP store moved from an in-process dict to Redis so it's
    shared across backend replicas -- this checks the actual Redis key
    Redis's own expiry (not a manual expires_at field) is what makes
    an old OTP eventually unusable."""
    from app.services import auth_service

    client.post("/auth/otp/request", json={"phone": "9996665555"})
    key = auth_service._otp_key("9996665555")
    assert auth_service.redis_client.get(key) == "1234"
    ttl = auth_service.redis_client.ttl(key)
    assert 0 < ttl <= auth_service.OTP_TTL_SECONDS


def test_verifying_an_otp_deletes_it_from_redis(client):
    from app.services import auth_service

    r = client.post("/auth/otp/request", json={"phone": "9995554444"})
    otp = r.json()["dev_otp"]
    client.post("/auth/otp/verify", json={"phone": "9995554444", "code": otp})

    key = auth_service._otp_key("9995554444")
    assert auth_service.redis_client.get(key) is None


def test_protected_endpoint_rejects_missing_token(client):
    r = client.get("/zones")
    assert r.status_code in (401, 403)


def test_protected_endpoint_rejects_garbage_token(client):
    r = client.get("/zones", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_protected_endpoint_accepts_a_real_token(client, make_user):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="correct-horse", email="coord4@test.dev")
    login = client.post("/auth/login", json={"email": "coord4@test.dev", "password": "correct-horse", "role": "central_coordinator"})
    token = login.json()["access_token"]
    r = client.get("/zones", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_login_is_rate_limited_after_five_attempts_per_minute(client, make_user):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="correct-horse", email="ratelimit1@test.dev")
    for _ in range(5):
        r = client.post("/auth/login", json={"email": "ratelimit1@test.dev", "password": "wrong", "role": "central_coordinator"})
        assert r.status_code == 401
    r = client.post("/auth/login", json={"email": "ratelimit1@test.dev", "password": "wrong", "role": "central_coordinator"})
    assert r.status_code == 429


def test_otp_request_is_rate_limited_after_five_attempts_per_minute(client):
    for i in range(5):
        r = client.post("/auth/otp/request", json={"phone": f"555000{i}"})
        assert r.status_code == 200
    r = client.post("/auth/otp/request", json={"phone": "5550009"})
    assert r.status_code == 429


def test_oversized_request_body_is_rejected(client, make_user):
    make_user(RoleEnum.CENTRAL_COORDINATOR, password="pw", email="bigbody@test.dev")
    headers_login = client.post("/auth/login", json={"email": "bigbody@test.dev", "password": "pw", "role": "central_coordinator"})
    token = headers_login.json()["access_token"]
    huge_description = "x" * 2_000_000  # 2MB, over the 1MB cap
    r = client.post(
        "/citizen-reports",
        json={"zone_id": 1, "description": huge_description},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 413

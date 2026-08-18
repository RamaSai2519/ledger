from conftest import signup

from shared.configs import CONFIG


def test_login_success(client):
    signup(client, mobile_number="9876543210", password="password123")
    resp = client.post("/auth/login", json={"mobile_number": "9876543210", "password": "password123"})
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["household_id"] is None


def test_login_wrong_password(client):
    signup(client, mobile_number="9876543210", password="password123")
    resp = client.post("/auth/login", json={"mobile_number": "9876543210", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "invalid_credentials"


def test_login_unknown_mobile_number(client):
    resp = client.post("/auth/login", json={"mobile_number": "9999999999", "password": "password123"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "invalid_credentials"


def test_login_missing_field_returns_400(client):
    resp = client.post("/auth/login", json={"mobile_number": "9876543210"})
    assert resp.status_code == 400


def test_login_locks_out_after_max_failed_attempts(client):
    signup(client, mobile_number="9876543210", password="password123")
    for _ in range(CONFIG["login_max_attempts"]):
        client.post("/auth/login", json={"mobile_number": "9876543210", "password": "wrongpassword"})

    resp = client.post("/auth/login", json={"mobile_number": "9876543210", "password": "password123"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "account_locked_try_later"


def test_refresh_returns_new_access_token(client):
    signup_resp = signup(client)
    refresh_token = signup_resp.get_json()["data"]["refresh_token"]
    resp = client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["access_token"]


def test_refresh_requires_a_refresh_token(client):
    signup_resp = signup(client)
    access_token = signup_resp.get_json()["data"]["access_token"]
    resp = client.post("/auth/refresh", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 422  # flask-jwt-extended rejects an access token where a refresh token is required


def test_logout_revokes_refresh_token(client):
    signup_resp = signup(client)
    refresh_token = signup_resp.get_json()["data"]["refresh_token"]

    logout_resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {refresh_token}"})
    assert logout_resp.status_code == 200

    reuse_resp = client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"})
    assert reuse_resp.status_code == 401

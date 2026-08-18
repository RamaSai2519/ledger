from conftest import signup


def test_signup_success(client):
    resp = signup(client)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "SUCCESS"
    assert body["data"]["name"] == "Rama"
    assert body["data"]["access_token"]
    assert body["data"]["refresh_token"]


def test_signup_missing_field_returns_400_not_500(client):
    resp = client.post("/auth/signup", json={"mobile_number": "9876543210", "password": "password123"})
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "FAILURE"


def test_signup_invalid_mobile_number(client):
    resp = signup(client, mobile_number="12345")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_mobile_number"


def test_signup_password_too_short(client):
    resp = signup(client, password="short")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "password_too_short"


def test_signup_duplicate_mobile_number_conflicts(client):
    signup(client)
    resp = signup(client)
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "mobile_number_already_registered"

from conftest import auth_headers, signup


def test_set_pin_success(client):
    token = signup(client).get_json()["data"]["access_token"]
    resp = client.post("/auth/pin", json={"pin": "1234"}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["pin_set"] is True


def test_set_pin_requires_auth(client):
    resp = client.post("/auth/pin", json={"pin": "1234"})
    assert resp.status_code == 401


def test_set_pin_rejects_non_numeric(client):
    token = signup(client).get_json()["data"]["access_token"]
    resp = client.post("/auth/pin", json={"pin": "abcd"}, headers=auth_headers(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "pin_must_be_4_to_6_digits"


def test_set_pin_rejects_wrong_length(client):
    token = signup(client).get_json()["data"]["access_token"]
    resp = client.post("/auth/pin", json={"pin": "123"}, headers=auth_headers(token))
    assert resp.status_code == 400

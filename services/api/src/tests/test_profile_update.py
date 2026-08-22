from conftest import auth_headers, signup


def _signup_and_token(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    return resp.get_json()["data"]["access_token"]


def test_profile_update_requires_auth(client):
    resp = client.patch("/users/profile", json={"name": "New Name"})
    assert resp.status_code == 401


def test_profile_update_name_success(client):
    token = _signup_and_token(client)
    resp = client.patch("/users/profile", json={"name": "Renamed"}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "Renamed"


def test_profile_update_accent_color_success(client):
    token = _signup_and_token(client)
    resp = client.patch("/users/profile", json={"accent_color": "#00FF00"}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["accent_color"] == "#00FF00"


def test_profile_update_persists_accent_color_for_household_members(client):
    token = _signup_and_token(client)
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    client.patch("/users/profile", json={"accent_color": "#00FF00"}, headers=auth_headers(token))

    resp = client.get("/auth/household/members", headers=auth_headers(token))
    assert resp.get_json()["data"]["members"][0]["accent_color"] == "#00FF00"


def test_profile_update_rejects_invalid_hex_color(client):
    token = _signup_and_token(client)
    resp = client.patch("/users/profile", json={"accent_color": "not-a-color"}, headers=auth_headers(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_accent_color_format"


def test_profile_update_rejects_blank_name(client):
    token = _signup_and_token(client)
    resp = client.patch("/users/profile", json={"name": "   "}, headers=auth_headers(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "name_required"


def test_profile_update_rejects_empty_body(client):
    token = _signup_and_token(client)
    resp = client.patch("/users/profile", json={}, headers=auth_headers(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "no_fields_to_update"


def test_profile_update_ignores_unrecognized_fields(client):
    token = _signup_and_token(client)
    resp = client.patch("/users/profile", json={"household_id": "abc123"}, headers=auth_headers(token))
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "no_recognized_fields_to_update"

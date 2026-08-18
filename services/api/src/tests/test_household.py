from conftest import auth_headers, signup


def _signup_and_token(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    return resp.get_json()["data"]["access_token"]


def test_create_household_success(client):
    token = _signup_and_token(client)
    resp = client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["name"] == "Our Home"
    assert len(body["invite_code"]) == 6


def test_create_household_requires_auth(client):
    resp = client.post("/auth/household/create", json={"name": "Our Home"})
    assert resp.status_code == 401


def test_create_household_twice_conflicts(client):
    token = _signup_and_token(client)
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    resp = client.post("/auth/household/create", json={"name": "Second"}, headers=auth_headers(token))
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "already_in_a_household"


def test_join_household_success(client):
    owner_token = _signup_and_token(client, mobile_number="9876543210", name="Rama")
    create_resp = client.post(
        "/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(owner_token)
    )
    invite_code = create_resp.get_json()["data"]["invite_code"]

    partner_token = _signup_and_token(client, mobile_number="9123456780", name="Partner")
    join_resp = client.post(
        "/auth/household/join", json={"invite_code": invite_code}, headers=auth_headers(partner_token)
    )
    assert join_resp.status_code == 200
    assert join_resp.get_json()["data"]["member_count"] == 2


def test_join_household_invalid_code(client):
    token = _signup_and_token(client)
    resp = client.post("/auth/household/join", json={"invite_code": "ZZZZZZ"}, headers=auth_headers(token))
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "invalid_invite_code"


def test_join_household_when_full(client):
    owner_token = _signup_and_token(client, mobile_number="9876543210", name="Rama")
    create_resp = client.post(
        "/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(owner_token)
    )
    invite_code = create_resp.get_json()["data"]["invite_code"]

    partner_token = _signup_and_token(client, mobile_number="9123456780", name="Partner")
    client.post("/auth/household/join", json={"invite_code": invite_code}, headers=auth_headers(partner_token))

    third_token = _signup_and_token(client, mobile_number="9111111111", name="Third")
    resp = client.post("/auth/household/join", json={"invite_code": invite_code}, headers=auth_headers(third_token))
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "household_full"


def test_invite_code_lookup_requires_household(client):
    token = _signup_and_token(client)
    resp = client.get("/auth/household/invite-code", headers=auth_headers(token))
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not_in_a_household"


def test_invite_code_lookup_success(client):
    token = _signup_and_token(client)
    create_resp = client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    invite_code = create_resp.get_json()["data"]["invite_code"]

    resp = client.get("/auth/household/invite-code", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["invite_code"] == invite_code

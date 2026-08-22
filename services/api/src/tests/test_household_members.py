from conftest import auth_headers, signup


def _signup_and_token(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    return resp.get_json()["data"]["access_token"]


def test_household_members_requires_auth(client):
    resp = client.get("/auth/household/members")
    assert resp.status_code == 401


def test_household_members_requires_household(client):
    token = _signup_and_token(client)
    resp = client.get("/auth/household/members", headers=auth_headers(token))
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not_in_a_household"


def test_household_members_lists_both_partners_with_accent_colors(client):
    owner_token = _signup_and_token(client, mobile_number="9876543210", name="Rama")
    create_resp = client.post(
        "/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(owner_token)
    )
    invite_code = create_resp.get_json()["data"]["invite_code"]

    partner_token = _signup_and_token(client, mobile_number="9123456780", name="Partner")
    client.post("/auth/household/join", json={"invite_code": invite_code}, headers=auth_headers(partner_token))

    resp = client.get("/auth/household/members", headers=auth_headers(owner_token))
    assert resp.status_code == 200
    members = resp.get_json()["data"]["members"]
    assert [m["name"] for m in members] == ["Rama", "Partner"]
    assert members[0]["accent_color"] == "#5B54F9"
    assert members[1]["accent_color"] == "#E8A33D"
    assert members[0]["accent_color"] != members[1]["accent_color"]


def test_household_members_only_sees_own_household(client):
    owner_token = _signup_and_token(client, mobile_number="9876543210", name="Rama")
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(owner_token))

    other_token = _signup_and_token(client, mobile_number="9111111111", name="Other")
    client.post("/auth/household/create", json={"name": "Other Home"}, headers=auth_headers(other_token))

    resp = client.get("/auth/household/members", headers=auth_headers(owner_token))
    members = resp.get_json()["data"]["members"]
    assert [m["name"] for m in members] == ["Rama"]

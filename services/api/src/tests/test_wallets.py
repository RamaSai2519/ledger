from conftest import auth_headers, signup


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _create_wallet(client, token, **overrides):
    body = {"name": "HDFC Savings", "type": "bank_account", "opening_balance": 1000}
    body.update(overrides)
    return client.post("/wallets", json=body, headers=auth_headers(token))


def test_create_wallet_success(client):
    token = _signup_household(client)
    resp = _create_wallet(client, token)
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["name"] == "HDFC Savings"
    assert body["type"] == "bank_account"
    assert body["current_balance"] == 1000
    assert body["opening_balance"] == 1000
    assert body["is_archived"] is False


def test_create_wallet_requires_auth(client):
    resp = _create_wallet(client, "bad-token")
    assert resp.status_code in (401, 422)


def test_create_wallet_invalid_type(client):
    token = _signup_household(client)
    resp = _create_wallet(client, token, type="crypto_wallet")
    assert resp.status_code == 400


def test_create_wallet_missing_name(client):
    token = _signup_household(client)
    resp = _create_wallet(client, token, name="")
    assert resp.status_code == 400


def test_create_credit_card_wallet_with_details(client):
    token = _signup_household(client)
    resp = _create_wallet(
        client,
        token,
        name="Axis Credit Card",
        type="credit_card",
        opening_balance=0,
        credit_card_details={"credit_limit": 100000, "statement_day": 3, "due_day": 20, "min_due_percent": 5},
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["credit_card_details"]["credit_limit"] == 100000


def test_list_wallets_household_scoped(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    _create_wallet(client, token_a, name="A Wallet")

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    _create_wallet(client, token_b, name="B Wallet")

    resp_a = client.get("/wallets", headers=auth_headers(token_a))
    names_a = [w["name"] for w in resp_a.get_json()["data"]["wallets"]]
    assert names_a == ["A Wallet"]

    resp_b = client.get("/wallets", headers=auth_headers(token_b))
    names_b = [w["name"] for w in resp_b.get_json()["data"]["wallets"]]
    assert names_b == ["B Wallet"]


def test_list_wallets_excludes_archived_by_default(client):
    token = _signup_household(client)
    create_resp = _create_wallet(client, token)
    wallet_id = create_resp.get_json()["data"]["id"]
    client.delete(f"/wallets/{wallet_id}", headers=auth_headers(token))

    resp = client.get("/wallets", headers=auth_headers(token))
    assert resp.get_json()["data"]["wallets"] == []

    resp_all = client.get("/wallets?include_archived=true", headers=auth_headers(token))
    assert len(resp_all.get_json()["data"]["wallets"]) == 1


def test_get_wallet_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    create_resp = _create_wallet(client, token_a)
    wallet_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token_b))
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "wallet_not_found"


def test_get_wallet_not_found(client):
    token = _signup_household(client)
    resp = client.get("/wallets/000000000000000000000000", headers=auth_headers(token))
    assert resp.status_code == 404


def test_update_wallet_success(client):
    token = _signup_household(client)
    create_resp = _create_wallet(client, token)
    wallet_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/wallets/{wallet_id}", json={"name": "Renamed"}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "Renamed"


def test_update_wallet_cannot_change_immutable_fields(client):
    token = _signup_household(client)
    create_resp = _create_wallet(client, token)
    wallet_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/wallets/{wallet_id}", json={"opening_balance": 5000}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_delete_wallet_archives_not_hard_deletes(client):
    token = _signup_household(client)
    create_resp = _create_wallet(client, token)
    wallet_id = create_resp.get_json()["data"]["id"]

    resp = client.delete(f"/wallets/{wallet_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["is_archived"] is True

    get_resp = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token))
    assert get_resp.status_code == 200
    assert get_resp.get_json()["data"]["is_archived"] is True


def test_reconcile_creates_adjustment_transaction_and_updates_balance(client):
    token = _signup_household(client)
    create_resp = _create_wallet(client, token, opening_balance=1000)
    wallet_id = create_resp.get_json()["data"]["id"]

    resp = client.post(
        f"/wallets/{wallet_id}/reconcile", json={"actual_balance": 1500}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["delta"] == 500
    assert body["wallet"]["current_balance"] == 1500
    assert body["adjustment_transaction"]["type"] == "adjustment"
    assert body["adjustment_transaction"]["amount"] == 500

    get_resp = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token))
    assert get_resp.get_json()["data"]["current_balance"] == 1500


def test_reconcile_negative_delta(client):
    token = _signup_household(client)
    create_resp = _create_wallet(client, token, opening_balance=1000)
    wallet_id = create_resp.get_json()["data"]["id"]

    resp = client.post(
        f"/wallets/{wallet_id}/reconcile", json={"actual_balance": 700}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["delta"] == -300
    assert resp.get_json()["data"]["wallet"]["current_balance"] == 700


def test_reconcile_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    create_resp = _create_wallet(client, token_a)
    wallet_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.post(
        f"/wallets/{wallet_id}/reconcile", json={"actual_balance": 999}, headers=auth_headers(token_b)
    )
    assert resp.status_code == 404


def test_balance_history_includes_opening_and_transactions(client):
    token = _signup_household(client)
    create_resp = _create_wallet(client, token, opening_balance=1000)
    wallet_id = create_resp.get_json()["data"]["id"]

    client.post(f"/wallets/{wallet_id}/reconcile", json={"actual_balance": 1200}, headers=auth_headers(token))

    resp = client.get(f"/wallets/{wallet_id}/balance-history", headers=auth_headers(token))
    assert resp.status_code == 200
    points = resp.get_json()["data"]["points"]
    assert points[0]["balance"] == 1000
    assert points[-1]["balance"] == 1200

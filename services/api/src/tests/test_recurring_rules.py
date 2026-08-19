from conftest import auth_headers, signup

from shared.db import get_transactions_collection


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _wallet(client, token, **overrides):
    body = {"name": "Cash", "type": "cash", "opening_balance": 1000}
    body.update(overrides)
    return client.post("/wallets", json=body, headers=auth_headers(token)).get_json()["data"]["id"]


def _category(client, token, name="Recur Test Category", type_="expense"):
    resp = client.post("/categories", json={"name": name, "type": type_}, headers=auth_headers(token))
    return resp.get_json()["data"]["id"]


def _create_rule(client, token, wallet_id, category_id, **overrides):
    body = {
        "wallet_id": wallet_id,
        "category_id": category_id,
        "type": "expense",
        "merchant_name": "Netflix",
        "frequency": "monthly",
        "next_due_date": "2026-01-31",
        "amount": 500,
    }
    body.update(overrides)
    return client.post("/recurring", json=body, headers=auth_headers(token))


def test_create_recurring_rule_success(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_rule(client, token, wallet_id, category_id)
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["merchant_name"] == "Netflix"
    assert body["frequency"] == "monthly"
    assert body["amount"] == 500
    assert body["auto_detected"] is False
    assert body["auto_create"] is False
    assert body["is_active"] is True
    assert body["next_due_date"].startswith("2026-01-31")


def test_create_recurring_rule_varies_amount(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_rule(client, token, wallet_id, category_id, amount=None)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["amount"] is None


def test_create_recurring_rule_invalid_frequency(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_rule(client, token, wallet_id, category_id, frequency="daily")
    assert resp.status_code == 400


def test_create_recurring_rule_wallet_not_found(client):
    token = _signup_household(client)
    category_id = _category(client, token)

    resp = _create_rule(client, token, "000000000000000000000000", category_id)
    assert resp.status_code == 404


def test_create_recurring_rule_category_not_found(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)

    resp = _create_rule(client, token, wallet_id, "000000000000000000000000")
    assert resp.status_code == 404


def test_create_recurring_rule_category_type_mismatch(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    income_category_id = _category(client, token, name="Recur Income Category", type_="income")

    resp = _create_rule(client, token, wallet_id, income_category_id, type="expense")
    assert resp.status_code == 400


def test_create_recurring_rule_negative_amount(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_rule(client, token, wallet_id, category_id, amount=-10)
    assert resp.status_code == 400


def test_create_recurring_rule_requires_auth(client):
    resp = client.post(
        "/recurring",
        json={
            "wallet_id": "x",
            "category_id": "y",
            "type": "expense",
            "merchant_name": "Netflix",
            "frequency": "monthly",
            "next_due_date": "2026-01-31",
        },
    )
    assert resp.status_code == 401


def test_list_recurring_rules_household_scoped(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    category_a = _category(client, token_a)
    _create_rule(client, token_a, wallet_a, category_a)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp_b = client.get("/recurring", headers=auth_headers(token_b))
    assert resp_b.get_json()["data"]["recurring_rules"] == []

    resp_a = client.get("/recurring", headers=auth_headers(token_a))
    assert len(resp_a.get_json()["data"]["recurring_rules"]) == 1


def test_list_recurring_rules_filter_is_active(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    _create_rule(client, token, wallet_id, category_id, is_active=True)
    _create_rule(client, token, wallet_id, category_id, is_active=False, merchant_name="Spotify")

    resp = client.get("/recurring?is_active=true", headers=auth_headers(token))
    rules = resp.get_json()["data"]["recurring_rules"]
    assert len(rules) == 1
    assert rules[0]["merchant_name"] == "Netflix"


def test_update_recurring_rule_partial(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_rule(client, token, wallet_id, category_id)
    rule_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/recurring/{rule_id}", json={"amount": 650}, headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["amount"] == 650
    assert body["merchant_name"] == "Netflix"


def test_update_recurring_rule_category_type_mismatch(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    income_category_id = _category(client, token, name="Recur Income Category", type_="income")
    create_resp = _create_rule(client, token, wallet_id, category_id)
    rule_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(
        f"/recurring/{rule_id}", json={"category_id": income_category_id}, headers=auth_headers(token)
    )
    assert resp.status_code == 400


def test_update_recurring_rule_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    category_a = _category(client, token_a)
    create_resp = _create_rule(client, token_a, wallet_a, category_a)
    rule_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.patch(f"/recurring/{rule_id}", json={"amount": 999}, headers=auth_headers(token_b))
    assert resp.status_code == 404


def test_delete_recurring_rule(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_rule(client, token, wallet_id, category_id)
    rule_id = create_resp.get_json()["data"]["id"]

    resp = client.delete(f"/recurring/{rule_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["deleted"] is True

    list_resp = client.get("/recurring", headers=auth_headers(token))
    assert list_resp.get_json()["data"]["recurring_rules"] == []


def test_delete_recurring_rule_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    category_a = _category(client, token_a)
    create_resp = _create_rule(client, token_a, wallet_a, category_a)
    rule_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.delete(f"/recurring/{rule_id}", headers=auth_headers(token_b))
    assert resp.status_code == 404


def test_delete_recurring_rule_does_not_touch_existing_transactions(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_rule(client, token, wallet_id, category_id)
    rule_id = create_resp.get_json()["data"]["id"]

    from bson import ObjectId

    txn_doc = {
        "household_id": ObjectId(),
        "wallet_id": ObjectId(wallet_id),
        "category_id": ObjectId(category_id),
        "user_id": ObjectId(),
        "type": "expense",
        "amount": 500,
        "transfer_to_wallet_id": None,
        "merchant_name": "Netflix",
        "note": None,
        "date": None,
        "source": "manual",
        "sms_id": None,
        "recurring_rule_id": ObjectId(rule_id),
        "created_at": None,
        "updated_at": None,
    }
    inserted = get_transactions_collection().insert_one(txn_doc)

    resp = client.delete(f"/recurring/{rule_id}", headers=auth_headers(token))
    assert resp.status_code == 200

    txn = get_transactions_collection().find_one({"_id": inserted.inserted_id})
    assert txn is not None
    assert str(txn["recurring_rule_id"]) == rule_id


def test_skip_next_weekly(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_rule(client, token, wallet_id, category_id, frequency="weekly", next_due_date="2026-01-01")
    rule_id = create_resp.get_json()["data"]["id"]

    resp = client.post(f"/recurring/{rule_id}/skip-next", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["next_due_date"].startswith("2026-01-08")


def test_skip_next_monthly_clamps_to_last_valid_day(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_rule(
        client, token, wallet_id, category_id, frequency="monthly", next_due_date="2026-01-31"
    )
    rule_id = create_resp.get_json()["data"]["id"]

    resp = client.post(f"/recurring/{rule_id}/skip-next", headers=auth_headers(token))
    assert resp.status_code == 200
    # 2026 is not a leap year, so Feb has 28 days.
    assert resp.get_json()["data"]["next_due_date"].startswith("2026-02-28")


def test_skip_next_yearly_clamps_feb29_to_non_leap_year(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_rule(
        client, token, wallet_id, category_id, frequency="yearly", next_due_date="2024-02-29"
    )
    rule_id = create_resp.get_json()["data"]["id"]

    resp = client.post(f"/recurring/{rule_id}/skip-next", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["next_due_date"].startswith("2025-02-28")


def test_skip_next_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    category_a = _category(client, token_a)
    create_resp = _create_rule(client, token_a, wallet_a, category_a)
    rule_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.post(f"/recurring/{rule_id}/skip-next", headers=auth_headers(token_b))
    assert resp.status_code == 404

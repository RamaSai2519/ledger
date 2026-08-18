from conftest import auth_headers, signup

from jobs.budget_threshold_check import run_budget_threshold_check
from shared.db import get_notifications_collection, get_users_collection


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    data = resp.get_json()["data"]
    token = data["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token, data["user_id"]


def _wallet(client, token):
    return client.post(
        "/wallets", json={"name": "Cash", "type": "cash", "opening_balance": 1000}, headers=auth_headers(token)
    ).get_json()["data"]["id"]


def _category(client, token, name="Coffee"):
    return client.post("/categories", json={"name": name, "type": "expense"}, headers=auth_headers(token)).get_json()[
        "data"
    ]["id"]


def _expense(client, token, wallet_id, category_id, amount):
    client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": amount},
        headers=auth_headers(token),
    )


def test_job_fires_notification_when_threshold_crossed(client):
    token, user_id = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    _expense(client, token, wallet_id, category_id, 850)  # 85% -> crosses 80

    fired = run_budget_threshold_check()
    assert len(fired) == 1
    assert fired[0]["threshold"] == 80

    notifications = list(get_notifications_collection().find({}))
    assert len(notifications) == 1
    assert notifications[0]["type"] == "budget_threshold"
    assert notifications[0]["user_id"] == get_users_collection().find_one({})["_id"]


def test_job_uses_budget_exceeded_type_at_100_percent(client):
    token, _ = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    _expense(client, token, wallet_id, category_id, 1000)  # 100%

    run_budget_threshold_check()
    notifications = list(get_notifications_collection().find({}))
    types = {n["type"] for n in notifications}
    assert "budget_exceeded" in types


def test_job_does_not_renotify_same_threshold_twice(client):
    token, _ = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    _expense(client, token, wallet_id, category_id, 850)

    fired_first = run_budget_threshold_check()
    fired_second = run_budget_threshold_check()

    assert len(fired_first) == 1
    assert len(fired_second) == 0
    assert get_notifications_collection().count_documents({}) == 1


def test_job_no_notification_below_threshold(client):
    token, _ = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    _expense(client, token, wallet_id, category_id, 100)  # 10%

    fired = run_budget_threshold_check()
    assert fired == []
    assert get_notifications_collection().count_documents({}) == 0


def test_job_creates_one_notification_per_household_member(client):
    token, _ = _signup_household(client)
    invite_code = client.get("/auth/household/invite-code", headers=auth_headers(token)).get_json()["data"][
        "invite_code"
    ]
    signup_resp = signup(client, mobile_number="9111111111", name="Partner")
    partner_token = signup_resp.get_json()["data"]["access_token"]
    client.post("/auth/household/join", json={"invite_code": invite_code}, headers=auth_headers(partner_token))

    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    _expense(client, token, wallet_id, category_id, 850)

    run_budget_threshold_check()
    assert get_notifications_collection().count_documents({}) == 2

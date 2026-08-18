from conftest import auth_headers, signup

from jobs.digest_notifications import run_daily_digest
from shared.db import get_notifications_collection


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


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


def test_digest_fires_one_notification_per_household(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    _expense(client, token, wallet_id, category_id, 300)

    sent = run_daily_digest()
    assert len(sent) == 1
    assert sent[0]["digest"]["total_spent"] == 300

    notifications = list(get_notifications_collection().find({}))
    assert len(notifications) == 1
    assert notifications[0]["type"] == "digest"


def test_digest_reports_top_category(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    coffee_id = _category(client, token, name="Coffee")
    groceries_id = _category(client, token, name="Snacks")
    _expense(client, token, wallet_id, coffee_id, 100)
    _expense(client, token, wallet_id, groceries_id, 900)

    sent = run_daily_digest()
    assert sent[0]["digest"]["top_category"] == "Snacks"


def test_digest_sent_for_household_with_no_transactions(client):
    _signup_household(client)
    sent = run_daily_digest()
    assert len(sent) == 1
    assert sent[0]["digest"]["total_spent"] == 0
    assert sent[0]["digest"]["top_category"] is None


def test_digest_household_scoped_totals(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    category_a = _category(client, token_a)
    _expense(client, token_a, wallet_a, category_a, 100)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    wallet_b = _wallet(client, token_b)
    category_b = _category(client, token_b)
    _expense(client, token_b, wallet_b, category_b, 500)

    sent = run_daily_digest()
    totals = {str(entry["household_id"]): entry["digest"]["total_spent"] for entry in sent}
    assert sorted(totals.values()) == [100, 500]

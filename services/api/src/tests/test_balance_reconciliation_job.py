from bson import ObjectId

from conftest import auth_headers, signup
from jobs.balance_reconciliation import run_balance_reconciliation
from shared.db import get_notifications_collection, get_wallets_collection


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _wallet(client, token, **overrides):
    body = {"name": "Cash", "type": "cash", "opening_balance": 1000}
    body.update(overrides)
    return client.post("/wallets", json=body, headers=auth_headers(token)).get_json()["data"]["id"]


def _category(client, token, name="Coffee", type_="expense"):
    resp = client.post("/categories", json={"name": name, "type": type_}, headers=auth_headers(token))
    return resp.get_json()["data"]["id"]


def test_no_drift_fires_no_notification(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 200},
        headers=auth_headers(token),
    )

    drifted = run_balance_reconciliation()
    assert drifted == []
    assert get_notifications_collection().count_documents({}) == 0


def test_drift_fires_exactly_one_balance_drift_notification(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, opening_balance=1000)
    category_id = _category(client, token)

    client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 200},
        headers=auth_headers(token),
    )

    # Manufacture drift: directly corrupt the cached current_balance,
    # bypassing the normal $inc write path.
    get_wallets_collection().update_one({"_id": ObjectId(wallet_id)}, {"$set": {"current_balance": 9999}})

    drifted = run_balance_reconciliation()
    assert len(drifted) == 1

    notifications = list(get_notifications_collection().find({"type": "balance_drift"}))
    assert len(notifications) == 1
    assert notifications[0]["payload"]["wallets"][0]["wallet_id"] == wallet_id

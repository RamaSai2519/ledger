from bson import ObjectId

from conftest import auth_headers, signup
from jobs.balance_reconciliation import reconcile_all_wallets, recompute_wallet_balance
from shared.db import get_wallets_collection


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


def test_reconcile_all_wallets_detects_no_drift_when_consistent(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 200},
        headers=auth_headers(token),
    )

    drifted = reconcile_all_wallets()
    assert drifted == []


def test_reconcile_all_wallets_flags_manufactured_drift(client):
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

    drifted = reconcile_all_wallets()
    assert len(drifted) == 1
    assert drifted[0]["wallet_id"] == ObjectId(wallet_id)
    assert drifted[0]["cached"] == 9999
    assert drifted[0]["recomputed"] == 800


def test_recompute_wallet_balance_includes_transfers_both_sides(client):
    token = _signup_household(client)
    wallet_1 = _wallet(client, token, name="W1", opening_balance=1000)
    wallet_2 = _wallet(client, token, name="W2", opening_balance=500)

    client.post(
        "/transactions/transfer",
        json={"wallet_id": wallet_1, "transfer_to_wallet_id": wallet_2, "amount": 300},
        headers=auth_headers(token),
    )

    w1 = get_wallets_collection().find_one({"_id": ObjectId(wallet_1)})
    w2 = get_wallets_collection().find_one({"_id": ObjectId(wallet_2)})

    assert recompute_wallet_balance(w1) == 700
    assert recompute_wallet_balance(w2) == 800


def test_reconcile_all_wallets_scoped_to_household(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    get_wallets_collection().update_one({"_id": ObjectId(wallet_a)}, {"$set": {"current_balance": -1}})

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    _wallet(client, token_b)

    user_b_household = get_wallets_collection().find_one({"_id": ObjectId(_wallet(client, token_b, name="W2"))})[
        "household_id"
    ]

    drifted = reconcile_all_wallets(household_id=user_b_household)
    assert drifted == []

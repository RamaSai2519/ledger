from datetime import datetime, timezone

from conftest import auth_headers, signup

from jobs.net_worth_snapshot import run_net_worth_snapshot
from shared.db import get_net_worth_snapshots_collection, get_users_collection


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _household_id_for(mobile_number):
    return get_users_collection().find_one({"mobile_number": mobile_number})["household_id"]


def _wallet(client, token, **overrides):
    body = {"name": "Cash", "type": "cash", "opening_balance": 1000}
    body.update(overrides)
    return client.post("/wallets", json=body, headers=auth_headers(token)).get_json()["data"]["id"]


def test_job_computes_assets_liabilities_and_net_worth(client):
    token = _signup_household(client)
    _wallet(client, token, name="Bank", type="bank_account", opening_balance=5000)
    _wallet(client, token, name="Card", type="credit_card", opening_balance=1500)

    results = run_net_worth_snapshot(now=datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc))
    assert len(results) == 1
    snapshot = results[0]
    assert snapshot["total_assets"] == 5000
    assert snapshot["total_liabilities"] == 1500
    assert snapshot["net_worth"] == 3500
    assert len(snapshot["per_wallet_breakdown"]) == 2

    stored = list(get_net_worth_snapshots_collection().find({}))
    assert len(stored) == 1
    # mongomock (like real PyMongo without tz_aware=True) round-trips
    # datetimes as naive UTC, so compare the naive form.
    assert stored[0]["date"].replace(tzinfo=None) == datetime(2026, 8, 19)


def test_job_is_idempotent_for_same_day(client):
    token = _signup_household(client)
    _wallet(client, token, name="Bank", type="bank_account", opening_balance=5000)

    run_net_worth_snapshot(now=datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc))
    run_net_worth_snapshot(now=datetime(2026, 8, 19, 20, 0, tzinfo=timezone.utc))

    assert get_net_worth_snapshots_collection().count_documents({}) == 1


def test_job_creates_one_snapshot_per_household(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    _wallet(client, token_a, name="Bank", type="bank_account", opening_balance=1000)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    _wallet(client, token_b, name="Bank", type="bank_account", opening_balance=2000)

    results = run_net_worth_snapshot(now=datetime(2026, 8, 19, tzinfo=timezone.utc))
    assert len(results) == 2

    household_a = _household_id_for("9876543210")
    household_b = _household_id_for("9111111111")
    snap_a = get_net_worth_snapshots_collection().find_one({"household_id": household_a})
    snap_b = get_net_worth_snapshots_collection().find_one({"household_id": household_b})
    assert snap_a["total_assets"] == 1000
    assert snap_b["total_assets"] == 2000


def test_job_ignores_archived_wallets(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, name="Old Wallet", type="cash", opening_balance=999)
    client.delete(f"/wallets/{wallet_id}", headers=auth_headers(token))

    results = run_net_worth_snapshot(now=datetime(2026, 8, 19, tzinfo=timezone.utc))
    assert results[0]["total_assets"] == 0

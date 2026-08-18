from datetime import datetime, timezone

from conftest import auth_headers, signup

from shared.db import get_net_worth_snapshots_collection, get_users_collection


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _household_id_for(token, mobile_number):
    user = get_users_collection().find_one({"mobile_number": mobile_number})
    return user["household_id"]


def _insert_snapshot(household_id, date, assets, liabilities):
    get_net_worth_snapshots_collection().insert_one(
        {
            "household_id": household_id,
            "date": date,
            "total_assets": assets,
            "total_liabilities": liabilities,
            "net_worth": assets - liabilities,
            "per_wallet_breakdown": {},
        }
    )


def test_net_worth_history_returns_snapshots_in_range(client):
    token = _signup_household(client)
    household_id = _household_id_for(token, "9876543210")

    _insert_snapshot(household_id, datetime(2026, 8, 1, tzinfo=timezone.utc), 10000, 2000)
    _insert_snapshot(household_id, datetime(2026, 8, 2, tzinfo=timezone.utc), 10500, 1800)
    _insert_snapshot(household_id, datetime(2026, 7, 1, tzinfo=timezone.utc), 9000, 2500)

    resp = client.get(
        "/insights/net-worth-history?from=2026-08-01&to=2026-08-31", headers=auth_headers(token)
    )
    assert resp.status_code == 200
    snapshots = resp.get_json()["data"]["snapshots"]
    assert len(snapshots) == 2
    assert snapshots[0]["net_worth"] == 8000
    assert snapshots[1]["net_worth"] == 8700


def test_net_worth_history_household_scoped(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    household_a = _household_id_for(token_a, "9876543210")
    _insert_snapshot(household_a, datetime(2026, 8, 1, tzinfo=timezone.utc), 10000, 2000)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.get(
        "/insights/net-worth-history?from=2026-08-01&to=2026-08-31", headers=auth_headers(token_b)
    )
    assert resp.get_json()["data"]["snapshots"] == []


def test_net_worth_history_invalid_date(client):
    token = _signup_household(client)
    resp = client.get("/insights/net-worth-history?from=not-a-date", headers=auth_headers(token))
    assert resp.status_code == 400


def test_net_worth_history_requires_auth(client):
    resp = client.get("/insights/net-worth-history")
    assert resp.status_code in (401, 422)

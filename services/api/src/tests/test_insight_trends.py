from datetime import datetime, timezone

from conftest import auth_headers, signup


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _wallet(client, token):
    return client.post(
        "/wallets", json={"name": "Cash", "type": "cash", "opening_balance": 1000}, headers=auth_headers(token)
    ).get_json()["data"]["id"]


def _category(client, token, name="Coffee", type_="expense"):
    return client.post("/categories", json={"name": name, "type": type_}, headers=auth_headers(token)).get_json()[
        "data"
    ]["id"]


def _txn(client, token, wallet_id, category_id, type_, amount, date):
    resp = client.post(
        "/transactions",
        json={
            "wallet_id": wallet_id,
            "category_id": category_id,
            "type": type_,
            "amount": amount,
            "date": date,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.get_json()
    return resp


def test_trends_daily_buckets_by_day(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    _txn(client, token, wallet_id, category_id, "expense", 100, "2026-08-10T10:00:00+00:00")
    _txn(client, token, wallet_id, category_id, "expense", 50, "2026-08-10T14:00:00+00:00")
    _txn(client, token, wallet_id, category_id, "expense", 25, "2026-08-11T09:00:00+00:00")

    resp = client.get(
        "/insights/trends?period=daily&from=2026-08-10&to=2026-08-11", headers=auth_headers(token)
    )
    assert resp.status_code == 200
    points = {p["bucket"]: p for p in resp.get_json()["data"]["points"]}
    assert points["2026-08-10"]["expense"] == 150
    assert points["2026-08-11"]["expense"] == 25


def test_trends_monthly_default_range_includes_zero_buckets(client):
    token = _signup_household(client)
    resp = client.get("/insights/trends?period=monthly", headers=auth_headers(token))
    assert resp.status_code == 200
    points = resp.get_json()["data"]["points"]
    assert len(points) == 12
    assert all(p["expense"] == 0 and p["income"] == 0 for p in points)


def test_trends_invalid_period(client):
    token = _signup_household(client)
    resp = client.get("/insights/trends?period=weekly", headers=auth_headers(token))
    assert resp.status_code == 400


def test_trends_requires_auth(client):
    resp = client.get("/insights/trends")
    assert resp.status_code in (401, 422)


def test_trends_household_scoped(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    category_a = _category(client, token_a)
    _txn(client, token_a, wallet_a, category_a, "expense", 500, "2026-08-10T10:00:00+00:00")

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.get(
        "/insights/trends?period=daily&from=2026-08-10&to=2026-08-10", headers=auth_headers(token_b)
    )
    points = resp.get_json()["data"]["points"]
    assert points[0]["expense"] == 0

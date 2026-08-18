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


def _category(client, token, name, color="#ff0000"):
    return client.post(
        "/categories", json={"name": name, "type": "expense", "color": color}, headers=auth_headers(token)
    ).get_json()["data"]["id"]


def _txn(client, token, wallet_id, category_id, amount, date):
    resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": amount, "date": date},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.get_json()


def test_category_breakdown_sorted_descending_with_denormalized_fields(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    food_id = _category(client, token, "Coffee", color="#00ff00")
    rent_id = _category(client, token, "Rent2", color="#0000ff")

    _txn(client, token, wallet_id, food_id, 200, "2026-08-10T10:00:00+00:00")
    _txn(client, token, wallet_id, rent_id, 900, "2026-08-10T10:00:00+00:00")

    resp = client.get(
        "/insights/category-breakdown?period=daily&from=2026-08-10&to=2026-08-10", headers=auth_headers(token)
    )
    assert resp.status_code == 200
    items = resp.get_json()["data"]["items"]
    assert len(items) == 2
    assert items[0]["category_name"] == "Rent2"
    assert items[0]["amount"] == 900
    assert items[0]["category_color"] == "#0000ff"
    assert items[1]["category_name"] == "Coffee"


def test_category_breakdown_excludes_income(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    food_id = _category(client, token, "Coffee")
    income_id = client.post(
        "/categories", json={"name": "Bonus", "type": "income"}, headers=auth_headers(token)
    ).get_json()["data"]["id"]

    _txn(client, token, wallet_id, food_id, 100, "2026-08-10T10:00:00+00:00")
    client.post(
        "/transactions",
        json={
            "wallet_id": wallet_id,
            "category_id": income_id,
            "type": "income",
            "amount": 5000,
            "date": "2026-08-10T10:00:00+00:00",
        },
        headers=auth_headers(token),
    )

    resp = client.get(
        "/insights/category-breakdown?period=daily&from=2026-08-10&to=2026-08-10", headers=auth_headers(token)
    )
    items = resp.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["category_name"] == "Coffee"


def test_category_breakdown_household_scoped(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    food_a = _category(client, token_a, "Food")
    _txn(client, token_a, wallet_a, food_a, 300, "2026-08-10T10:00:00+00:00")

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.get(
        "/insights/category-breakdown?period=daily&from=2026-08-10&to=2026-08-10", headers=auth_headers(token_b)
    )
    assert resp.get_json()["data"]["items"] == []


def test_category_breakdown_invalid_period(client):
    token = _signup_household(client)
    resp = client.get("/insights/category-breakdown?period=hourly", headers=auth_headers(token))
    assert resp.status_code == 400


def test_category_breakdown_requires_auth(client):
    resp = client.get("/insights/category-breakdown")
    assert resp.status_code in (401, 422)

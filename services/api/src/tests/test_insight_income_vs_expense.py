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


def _category(client, token, name, type_):
    return client.post("/categories", json={"name": name, "type": type_}, headers=auth_headers(token)).get_json()[
        "data"
    ]["id"]


def _txn(client, token, wallet_id, category_id, type_, amount, date):
    resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": type_, "amount": amount, "date": date},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.get_json()


def test_income_vs_expense_side_by_side(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    expense_cat = _category(client, token, "Coffee", "expense")
    income_cat = _category(client, token, "Bonus", "income")

    _txn(client, token, wallet_id, expense_cat, "expense", 300, "2026-08-10T10:00:00+00:00")
    _txn(client, token, wallet_id, income_cat, "income", 1000, "2026-08-10T10:00:00+00:00")

    resp = client.get(
        "/insights/income-vs-expense?period=daily&from=2026-08-10&to=2026-08-10", headers=auth_headers(token)
    )
    assert resp.status_code == 200
    point = resp.get_json()["data"]["points"][0]
    assert point["income"] == 1000
    assert point["expense"] == 300
    assert point["net"] == 700


def test_income_vs_expense_invalid_period(client):
    token = _signup_household(client)
    resp = client.get("/insights/income-vs-expense?period=bogus", headers=auth_headers(token))
    assert resp.status_code == 400


def test_income_vs_expense_requires_auth(client):
    resp = client.get("/insights/income-vs-expense")
    assert resp.status_code in (401, 422)


def test_income_vs_expense_invalid_date_range(client):
    token = _signup_household(client)
    resp = client.get(
        "/insights/income-vs-expense?period=daily&from=2026-08-15&to=2026-08-01", headers=auth_headers(token)
    )
    assert resp.status_code == 400

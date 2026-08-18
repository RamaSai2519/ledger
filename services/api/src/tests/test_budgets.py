from conftest import auth_headers, signup


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


def _expense(client, token, wallet_id, category_id, amount):
    return client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": amount},
        headers=auth_headers(token),
    )


def test_create_overall_budget_success(client):
    token = _signup_household(client)
    resp = client.post("/budgets", json={"scope": "overall", "amount": 5000}, headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["scope"] == "overall"
    assert body["scope_ref_id"] is None
    assert body["threshold_percents"] == [80, 100]


def test_create_budget_custom_thresholds(client):
    token = _signup_household(client)
    resp = client.post(
        "/budgets",
        json={"scope": "overall", "amount": 5000, "threshold_percents": [50, 90]},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["threshold_percents"] == [50, 90]


def test_create_category_budget_resolves_scope_ref(client):
    token = _signup_household(client)
    category_id = _category(client, token)
    resp = client.post(
        "/budgets", json={"scope": "category", "scope_ref_id": category_id, "amount": 1000}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["scope_ref_id"] == category_id


def test_create_wallet_budget_resolves_scope_ref(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    resp = client.post(
        "/budgets", json={"scope": "wallet", "scope_ref_id": wallet_id, "amount": 1000}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["scope_ref_id"] == wallet_id


def test_create_budget_invalid_scope(client):
    token = _signup_household(client)
    resp = client.post("/budgets", json={"scope": "yearly", "amount": 1000}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_create_category_budget_missing_scope_ref_id(client):
    token = _signup_household(client)
    resp = client.post("/budgets", json={"scope": "category", "amount": 1000}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_create_category_budget_cross_household_category_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    category_id = _category(client, token_a)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.post(
        "/budgets", json={"scope": "category", "scope_ref_id": category_id, "amount": 1000}, headers=auth_headers(token_b)
    )
    assert resp.status_code == 404


def test_create_budget_negative_amount(client):
    token = _signup_household(client)
    resp = client.post("/budgets", json={"scope": "overall", "amount": -5}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_create_budget_requires_auth(client):
    resp = client.post("/budgets", json={"scope": "overall", "amount": 5000})
    assert resp.status_code == 401


def test_list_budgets_household_scoped(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token_a))

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp_b = client.get("/budgets", headers=auth_headers(token_b))
    assert resp_b.get_json()["data"]["budgets"] == []

    resp_a = client.get("/budgets", headers=auth_headers(token_a))
    assert len(resp_a.get_json()["data"]["budgets"]) == 1


def test_update_budget_amount(client):
    token = _signup_household(client)
    create_resp = client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    budget_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/budgets/{budget_id}", json={"amount": 2000}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["amount"] == 2000


def test_update_budget_cannot_change_scope(client):
    token = _signup_household(client)
    create_resp = client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    budget_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/budgets/{budget_id}", json={"scope": "category"}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_update_budget_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    create_resp = client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token_a))
    budget_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.patch(f"/budgets/{budget_id}", json={"amount": 500}, headers=auth_headers(token_b))
    assert resp.status_code == 404


def test_delete_budget(client):
    token = _signup_household(client)
    create_resp = client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    budget_id = create_resp.get_json()["data"]["id"]

    resp = client.delete(f"/budgets/{budget_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["deleted"] is True

    list_resp = client.get("/budgets", headers=auth_headers(token))
    assert list_resp.get_json()["data"]["budgets"] == []


def test_budget_progress_overall(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    budget_resp = client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    budget_id = budget_resp.get_json()["data"]["id"]

    _expense(client, token, wallet_id, category_id, 400)

    resp = client.get(f"/budgets/{budget_id}/progress", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["spent"] == 400
    assert body["amount"] == 1000
    assert body["percent"] == 40.0
    assert body["crossed_thresholds"] == []


def test_budget_progress_crosses_threshold(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    budget_resp = client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token))
    budget_id = budget_resp.get_json()["data"]["id"]

    _expense(client, token, wallet_id, category_id, 850)

    resp = client.get(f"/budgets/{budget_id}/progress", headers=auth_headers(token))
    body = resp.get_json()["data"]
    assert body["percent"] == 85.0
    assert body["crossed_thresholds"] == [80]


def test_budget_progress_category_scope_only_counts_that_category(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    coffee_id = _category(client, token, name="Coffee")
    rent_id = _category(client, token, name="Rent2", type_="expense")
    budget_resp = client.post(
        "/budgets", json={"scope": "category", "scope_ref_id": coffee_id, "amount": 200}, headers=auth_headers(token)
    )
    budget_id = budget_resp.get_json()["data"]["id"]

    _expense(client, token, wallet_id, coffee_id, 100)
    _expense(client, token, wallet_id, rent_id, 5000)  # different category, should not count

    resp = client.get(f"/budgets/{budget_id}/progress", headers=auth_headers(token))
    assert resp.get_json()["data"]["spent"] == 100


def test_budget_progress_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    create_resp = client.post("/budgets", json={"scope": "overall", "amount": 1000}, headers=auth_headers(token_a))
    budget_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.get(f"/budgets/{budget_id}/progress", headers=auth_headers(token_b))
    assert resp.status_code == 404

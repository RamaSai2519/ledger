from conftest import auth_headers, signup


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _wallet(client, token, **overrides):
    body = {"name": "Bank", "type": "bank_account", "opening_balance": 1000}
    body.update(overrides)
    return client.post("/wallets", json=body, headers=auth_headers(token)).get_json()["data"]["id"]


def _category(client, token, name="Loan Payment", type_="expense"):
    resp = client.post("/categories", json={"name": name, "type": type_}, headers=auth_headers(token))
    return resp.get_json()["data"]["id"]


def _create_loan(client, token, wallet_id, category_id, **overrides):
    body = {
        "name": "Bike Loan",
        "wallet_id": wallet_id,
        "category_id": category_id,
        "principal": 96000,
        "annual_interest_rate": 12,
        "tenure_months": 24,
        "emi_amount": 4500,
        "start_date": "2026-01-01",
    }
    body.update(overrides)
    return client.post("/loans", json=body, headers=auth_headers(token))


def test_create_loan_success(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_loan(client, token, wallet_id, category_id)
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["name"] == "Bike Loan"
    assert body["principal"] == 96000
    assert body["outstanding_balance"] == 96000
    assert body["emi_amount"] == 4500
    assert body["is_active"] is True
    assert body["next_due_date"].startswith("2026-02-01")


def test_create_loan_missing_name(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_loan(client, token, wallet_id, category_id, name="")
    assert resp.status_code == 400


def test_create_loan_bad_wallet_id(client):
    token = _signup_household(client)
    category_id = _category(client, token)

    resp = _create_loan(client, token, "000000000000000000000000", category_id)
    assert resp.status_code == 404


def test_create_loan_bad_category_id(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)

    resp = _create_loan(client, token, wallet_id, "000000000000000000000000")
    assert resp.status_code == 404


def test_create_loan_non_positive_principal(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_loan(client, token, wallet_id, category_id, principal=0)
    assert resp.status_code == 400


def test_create_loan_negative_interest_rate(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_loan(client, token, wallet_id, category_id, annual_interest_rate=-1)
    assert resp.status_code == 400


def test_create_loan_non_positive_tenure(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_loan(client, token, wallet_id, category_id, tenure_months=0)
    assert resp.status_code == 400


def test_create_loan_non_positive_emi_amount(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = _create_loan(client, token, wallet_id, category_id, emi_amount=0)
    assert resp.status_code == 400


def test_create_loan_requires_auth(client):
    resp = client.post(
        "/loans",
        json={
            "name": "Bike Loan",
            "wallet_id": "x",
            "category_id": "y",
            "principal": 96000,
            "annual_interest_rate": 12,
            "tenure_months": 24,
            "emi_amount": 4500,
            "start_date": "2026-01-01",
        },
    )
    assert resp.status_code == 401


def test_list_loans_household_scoped(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    category_a = _category(client, token_a)
    _create_loan(client, token_a, wallet_a, category_a)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp_b = client.get("/loans", headers=auth_headers(token_b))
    assert resp_b.get_json()["data"]["loans"] == []

    resp_a = client.get("/loans", headers=auth_headers(token_a))
    assert len(resp_a.get_json()["data"]["loans"]) == 1


def test_list_loans_filter_is_active(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    resp = _create_loan(client, token, wallet_id, category_id)
    loan_id = resp.get_json()["data"]["id"]
    client.patch(f"/loans/{loan_id}", json={"is_active": False}, headers=auth_headers(token))
    _create_loan(client, token, wallet_id, category_id, name="Car Loan")

    resp = client.get("/loans?is_active=true", headers=auth_headers(token))
    loans = resp.get_json()["data"]["loans"]
    assert len(loans) == 1
    assert loans[0]["name"] == "Car Loan"


def test_update_loan_patchable_field(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_loan(client, token, wallet_id, category_id)
    loan_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/loans/{loan_id}", json={"emi_amount": 5000}, headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["emi_amount"] == 5000
    assert body["name"] == "Bike Loan"


def test_update_loan_immutable_field_rejected(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_loan(client, token, wallet_id, category_id)
    loan_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/loans/{loan_id}", json={"principal": 50000}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_update_loan_outstanding_balance_immutable(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_loan(client, token, wallet_id, category_id)
    loan_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/loans/{loan_id}", json={"outstanding_balance": 1}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_update_loan_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    category_a = _category(client, token_a)
    create_resp = _create_loan(client, token_a, wallet_a, category_a)
    loan_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.patch(f"/loans/{loan_id}", json={"emi_amount": 999}, headers=auth_headers(token_b))
    assert resp.status_code == 404


def test_delete_loan(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    create_resp = _create_loan(client, token, wallet_id, category_id)
    loan_id = create_resp.get_json()["data"]["id"]

    resp = client.delete(f"/loans/{loan_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["deleted"] is True

    list_resp = client.get("/loans", headers=auth_headers(token))
    assert list_resp.get_json()["data"]["loans"] == []


def test_delete_loan_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)
    category_a = _category(client, token_a)
    create_resp = _create_loan(client, token_a, wallet_a, category_a)
    loan_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.delete(f"/loans/{loan_id}", headers=auth_headers(token_b))
    assert resp.status_code == 404

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


def test_create_expense_transaction_decrements_asset_wallet(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 200},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["type"] == "expense"

    wallet_resp = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token))
    assert wallet_resp.get_json()["data"]["current_balance"] == 800


def test_create_income_transaction_increments_asset_wallet(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token, name="Bonus", type_="income")

    client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "income", "amount": 500},
        headers=auth_headers(token),
    )
    wallet_resp = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token))
    assert wallet_resp.get_json()["data"]["current_balance"] == 1500


def test_create_expense_on_credit_card_increases_liability(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, name="Axis CC", type="credit_card", opening_balance=0)
    category_id = _category(client, token)

    client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 300},
        headers=auth_headers(token),
    )
    wallet_resp = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token))
    assert wallet_resp.get_json()["data"]["current_balance"] == 300


def test_create_transaction_validation_failure_negative_amount(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": -10},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


def test_create_transaction_category_type_mismatch(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token, name="Bonus", type_="income")

    resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 10},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


def test_create_transaction_cross_household_wallet_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_id = _wallet(client, token_a)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    category_id_b = _category(client, token_b)

    resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id_b, "type": "expense", "amount": 10},
        headers=auth_headers(token_b),
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "wallet_not_found"


def test_list_transactions_filters_and_pagination(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)

    for amount in (10, 20, 30):
        client.post(
            "/transactions",
            json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": amount},
            headers=auth_headers(token),
        )

    resp = client.get(f"/transactions?wallet_id={wallet_id}&page=1&page_size=2", headers=auth_headers(token))
    body = resp.get_json()["data"]
    assert body["total"] == 3
    assert len(body["transactions"]) == 2
    assert body["has_more"] is True


def test_get_transaction_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_id = _wallet(client, token_a)
    category_id = _category(client, token_a)
    create_resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 10},
        headers=auth_headers(token_a),
    )
    txn_id = create_resp.get_json()["data"]["id"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.get(f"/transactions/{txn_id}", headers=auth_headers(token_b))
    assert resp.status_code == 404


def test_update_transaction_amount_reverses_and_reapplies_delta(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, opening_balance=1000)
    category_id = _category(client, token)

    create_resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 100},
        headers=auth_headers(token),
    )
    txn_id = create_resp.get_json()["data"]["id"]

    wallet_resp = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token))
    assert wallet_resp.get_json()["data"]["current_balance"] == 900

    resp = client.patch(f"/transactions/{txn_id}", json={"amount": 250}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["amount"] == 250

    wallet_resp = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token))
    assert wallet_resp.get_json()["data"]["current_balance"] == 750


def test_update_transaction_change_wallet_moves_balance_effect(client):
    token = _signup_household(client)
    wallet_1 = _wallet(client, token, name="W1", opening_balance=1000)
    wallet_2 = _wallet(client, token, name="W2", opening_balance=1000)
    category_id = _category(client, token)

    create_resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_1, "category_id": category_id, "type": "expense", "amount": 100},
        headers=auth_headers(token),
    )
    txn_id = create_resp.get_json()["data"]["id"]

    client.patch(f"/transactions/{txn_id}", json={"wallet_id": wallet_2}, headers=auth_headers(token))

    w1 = client.get(f"/wallets/{wallet_1}", headers=auth_headers(token)).get_json()["data"]
    w2 = client.get(f"/wallets/{wallet_2}", headers=auth_headers(token)).get_json()["data"]
    assert w1["current_balance"] == 1000
    assert w2["current_balance"] == 900


def test_update_transfer_transaction_blocked(client):
    token = _signup_household(client)
    wallet_1 = _wallet(client, token, name="W1")
    wallet_2 = _wallet(client, token, name="W2")

    transfer_resp = client.post(
        "/transactions/transfer",
        json={"wallet_id": wallet_1, "transfer_to_wallet_id": wallet_2, "amount": 100},
        headers=auth_headers(token),
    )
    txn_id = transfer_resp.get_json()["data"]["id"]

    resp = client.patch(f"/transactions/{txn_id}", json={"amount": 200}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_delete_transaction_reverses_balance(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, opening_balance=1000)
    category_id = _category(client, token)

    create_resp = client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 100},
        headers=auth_headers(token),
    )
    txn_id = create_resp.get_json()["data"]["id"]

    resp = client.delete(f"/transactions/{txn_id}", headers=auth_headers(token))
    assert resp.status_code == 200

    wallet_resp = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token))
    assert wallet_resp.get_json()["data"]["current_balance"] == 1000


def test_delete_transfer_transaction_reverses_both_wallets(client):
    token = _signup_household(client)
    wallet_1 = _wallet(client, token, name="W1", opening_balance=1000)
    wallet_2 = _wallet(client, token, name="W2", opening_balance=1000)

    transfer_resp = client.post(
        "/transactions/transfer",
        json={"wallet_id": wallet_1, "transfer_to_wallet_id": wallet_2, "amount": 300},
        headers=auth_headers(token),
    )
    txn_id = transfer_resp.get_json()["data"]["id"]

    w1 = client.get(f"/wallets/{wallet_1}", headers=auth_headers(token)).get_json()["data"]
    w2 = client.get(f"/wallets/{wallet_2}", headers=auth_headers(token)).get_json()["data"]
    assert w1["current_balance"] == 700
    assert w2["current_balance"] == 1300

    client.delete(f"/transactions/{txn_id}", headers=auth_headers(token))

    w1 = client.get(f"/wallets/{wallet_1}", headers=auth_headers(token)).get_json()["data"]
    w2 = client.get(f"/wallets/{wallet_2}", headers=auth_headers(token)).get_json()["data"]
    assert w1["current_balance"] == 1000
    assert w2["current_balance"] == 1000


def test_transfer_to_credit_card_reduces_liability(client):
    token = _signup_household(client)
    bank = _wallet(client, token, name="Bank", type="bank_account", opening_balance=5000)
    cc = _wallet(client, token, name="CC", type="credit_card", opening_balance=1000)

    resp = client.post(
        "/transactions/transfer",
        json={"wallet_id": bank, "transfer_to_wallet_id": cc, "amount": 400},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["type"] == "transfer"

    bank_resp = client.get(f"/wallets/{bank}", headers=auth_headers(token)).get_json()["data"]
    cc_resp = client.get(f"/wallets/{cc}", headers=auth_headers(token)).get_json()["data"]
    assert bank_resp["current_balance"] == 4600
    assert cc_resp["current_balance"] == 600


def test_transfer_same_wallet_rejected(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)

    resp = client.post(
        "/transactions/transfer",
        json={"wallet_id": wallet_id, "transfer_to_wallet_id": wallet_id, "amount": 100},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


def test_transfer_cross_household_destination_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    wallet_a = _wallet(client, token_a)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    wallet_b = _wallet(client, token_b)

    resp = client.post(
        "/transactions/transfer",
        json={"wallet_id": wallet_a, "transfer_to_wallet_id": wallet_b, "amount": 100},
        headers=auth_headers(token_a),
    )
    assert resp.status_code == 404

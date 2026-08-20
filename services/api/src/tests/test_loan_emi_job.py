from datetime import datetime

from bson import ObjectId
from conftest import auth_headers, signup

from jobs.loan_emi_check import run_loan_emi_check
from shared.db import get_loans_collection, get_transactions_collection, get_wallets_collection


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _wallet(client, token, **overrides):
    body = {"name": "Bank", "type": "bank_account", "opening_balance": 100000}
    body.update(overrides)
    resp = client.post("/wallets", json=body, headers=auth_headers(token)).get_json()["data"]
    return resp["id"]


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
    resp = client.post("/loans", json=body, headers=auth_headers(token))
    return resp.get_json()["data"]["id"]


def test_due_loan_creates_transaction_and_decrements_outstanding_balance(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    loan_id = _create_loan(client, token, wallet_id, category_id)  # next_due_date = 2026-02-01

    today = datetime(2026, 2, 15)
    result = run_loan_emi_check(today=today)

    assert len(result) == 1
    assert result[0]["action"] == "emi_paid"
    assert result[0]["transaction_id"] is not None

    # interest = 96000 * (12/12/100) = 960; principal = 4500 - 960 = 3540
    txn = get_transactions_collection().find_one({"_id": result[0]["transaction_id"]})
    assert txn is not None
    assert txn["type"] == "expense"
    assert txn["amount"] == 4500
    assert txn["loan_id"] == ObjectId(loan_id)
    assert txn["date"] == datetime(2026, 2, 1)

    wallet = get_wallets_collection().find_one({"_id": ObjectId(wallet_id)})
    assert wallet["current_balance"] == 100000 - 4500

    loan = get_loans_collection().find_one({"_id": ObjectId(loan_id)})
    assert loan["outstanding_balance"] == 96000 - 3540
    assert loan["next_due_date"] == datetime(2026, 3, 1)
    assert loan["is_active"] is True


def test_final_payment_pays_exact_remainder_and_closes_loan(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    loan_id = _create_loan(
        client,
        token,
        wallet_id,
        category_id,
        principal=1000,
        annual_interest_rate=0,
        emi_amount=4500,
    )

    today = datetime(2026, 2, 15)
    result = run_loan_emi_check(today=today)

    assert len(result) == 1
    txn = get_transactions_collection().find_one({"_id": result[0]["transaction_id"]})
    # 0% interest, principal_component would be 4500 which overshoots the
    # 1000 outstanding balance -> clamped to pay exactly 1000.
    assert txn["amount"] == 1000

    loan = get_loans_collection().find_one({"_id": ObjectId(loan_id)})
    assert loan["outstanding_balance"] == 0
    assert loan["is_active"] is False


def test_not_yet_due_loan_untouched(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    loan_id = _create_loan(client, token, wallet_id, category_id, start_date="2026-06-01")  # due 2026-07-01

    today = datetime(2026, 2, 15)
    result = run_loan_emi_check(today=today)

    assert result == []
    loan = get_loans_collection().find_one({"_id": ObjectId(loan_id)})
    assert loan["next_due_date"] == datetime(2026, 7, 1)
    assert loan["outstanding_balance"] == 96000


def test_inactive_loan_skipped(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    loan_id = _create_loan(client, token, wallet_id, category_id)
    client.patch(f"/loans/{loan_id}", json={"is_active": False}, headers=auth_headers(token))

    today = datetime(2026, 2, 15)
    result = run_loan_emi_check(today=today)

    assert result == []
    loan = get_loans_collection().find_one({"_id": ObjectId(loan_id)})
    assert loan["next_due_date"] == datetime(2026, 2, 1)

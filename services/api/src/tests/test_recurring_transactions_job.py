from datetime import datetime

from bson import ObjectId
from conftest import auth_headers, signup

from jobs.recurring_transactions_check import run_recurring_transactions_check
from shared.db import (
    get_notifications_collection,
    get_recurring_rules_collection,
    get_transactions_collection,
    get_wallets_collection,
)


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _wallet(client, token, **overrides):
    body = {"name": "Cash", "type": "cash", "opening_balance": 1000}
    body.update(overrides)
    resp = client.post("/wallets", json=body, headers=auth_headers(token)).get_json()["data"]
    return resp["id"]


def _category(client, token, name="Recur Test Category", type_="expense"):
    resp = client.post("/categories", json={"name": name, "type": type_}, headers=auth_headers(token))
    return resp.get_json()["data"]["id"]


def _create_rule(client, token, wallet_id, category_id, **overrides):
    body = {
        "wallet_id": wallet_id,
        "category_id": category_id,
        "type": "expense",
        "merchant_name": "Netflix",
        "frequency": "monthly",
        "next_due_date": "2026-01-01",
        "amount": 500,
    }
    body.update(overrides)
    resp = client.post("/recurring", json=body, headers=auth_headers(token))
    return resp.get_json()["data"]["id"]


def test_due_auto_create_rule_creates_transaction_and_updates_balance(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, opening_balance=1000)
    category_id = _category(client, token)
    rule_id = _create_rule(client, token, wallet_id, category_id, auto_create=True, amount=500)


    today = datetime(2026, 1, 15)
    result = run_recurring_transactions_check(today=today)

    assert len(result) == 1
    assert result[0]["action"] == "auto_created"
    assert result[0]["transaction_id"] is not None

    txn = get_transactions_collection().find_one({"_id": result[0]["transaction_id"]})
    assert txn is not None
    assert txn["source"] == "manual"
    assert txn["recurring_rule_id"] == ObjectId(rule_id)
    assert txn["amount"] == 500
    assert txn["date"] == datetime(2026, 1, 1)

    wallet = get_wallets_collection().find_one({"_id": ObjectId(wallet_id)})
    assert wallet["current_balance"] == 500  # 1000 - 500 expense

    rule = get_recurring_rules_collection().find_one({"_id": ObjectId(rule_id)})
    assert rule["next_due_date"] == datetime(2026, 2, 1)

    # no reminder notification for an auto-created rule
    assert get_notifications_collection().find_one({"type": "recurring_reminder"}) is None


def test_due_auto_create_rule_with_no_amount_sends_reminder_instead(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    rule_id = _create_rule(client, token, wallet_id, category_id, auto_create=True, amount=None)


    today = datetime(2026, 1, 15)
    result = run_recurring_transactions_check(today=today)

    assert len(result) == 1
    assert result[0]["action"] == "reminder_sent"
    assert result[0]["transaction_id"] is None

    assert get_transactions_collection().find_one({"recurring_rule_id": ObjectId(rule_id)}) is None
    assert get_notifications_collection().find_one({"type": "recurring_reminder"}) is not None

    rule = get_recurring_rules_collection().find_one({"_id": ObjectId(rule_id)})
    assert rule["next_due_date"] == datetime(2026, 2, 1)


def test_due_auto_create_false_rule_sends_reminder(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    rule_id = _create_rule(client, token, wallet_id, category_id, auto_create=False)


    today = datetime(2026, 1, 15)
    result = run_recurring_transactions_check(today=today)

    assert len(result) == 1
    assert result[0]["action"] == "reminder_sent"
    assert get_transactions_collection().find_one({"recurring_rule_id": ObjectId(rule_id)}) is None
    assert get_notifications_collection().find_one({"type": "recurring_reminder"}) is not None

    rule = get_recurring_rules_collection().find_one({"_id": ObjectId(rule_id)})
    assert rule["next_due_date"] == datetime(2026, 2, 1)


def test_not_yet_due_rule_untouched(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    rule_id = _create_rule(client, token, wallet_id, category_id, next_due_date="2026-06-01")


    today = datetime(2026, 1, 15)
    result = run_recurring_transactions_check(today=today)

    assert result == []
    assert get_notifications_collection().find_one({"type": "recurring_reminder"}) is None

    rule = get_recurring_rules_collection().find_one({"_id": ObjectId(rule_id)})
    assert rule["next_due_date"] == datetime(2026, 6, 1)


def test_inactive_rule_skipped_entirely(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token)
    category_id = _category(client, token)
    rule_id = _create_rule(client, token, wallet_id, category_id, is_active=False)


    today = datetime(2026, 1, 15)
    result = run_recurring_transactions_check(today=today)

    assert result == []
    rule = get_recurring_rules_collection().find_one({"_id": ObjectId(rule_id)})
    assert rule["next_due_date"] == datetime(2026, 1, 1)

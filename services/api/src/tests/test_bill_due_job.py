from datetime import date, timedelta

from conftest import auth_headers, signup

from jobs.bill_due_reminders import run_bill_due_reminders
from shared.db import get_notifications_collection


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _credit_card(client, token, due_day):
    return client.post(
        "/wallets",
        json={
            "name": "Axis Credit Card",
            "type": "credit_card",
            "opening_balance": 0,
            "credit_card_details": {"credit_limit": 100000, "statement_day": 3, "due_day": due_day, "min_due_percent": 5},
        },
        headers=auth_headers(token),
    ).get_json()["data"]["id"]


def test_fires_reminder_when_due_within_window(client):
    token = _signup_household(client)
    today = date(2026, 1, 10)
    due_day = (today + timedelta(days=2)).day
    _credit_card(client, token, due_day)

    fired = run_bill_due_reminders(today=today)
    assert len(fired) == 1

    notifications = list(get_notifications_collection().find({}))
    assert notifications[0]["type"] == "bill_due"


def test_no_reminder_when_due_date_far_away(client):
    token = _signup_household(client)
    today = date(2026, 1, 1)
    due_day = (today + timedelta(days=20)).day
    _credit_card(client, token, due_day)

    fired = run_bill_due_reminders(today=today)
    assert fired == []
    assert get_notifications_collection().count_documents({}) == 0


def test_does_not_renotify_same_due_date(client):
    token = _signup_household(client)
    today = date(2026, 1, 10)
    due_day = (today + timedelta(days=1)).day
    _credit_card(client, token, due_day)

    first = run_bill_due_reminders(today=today)
    second = run_bill_due_reminders(today=today)

    assert len(first) == 1
    assert len(second) == 0
    assert get_notifications_collection().count_documents({}) == 1


def test_ignores_wallets_without_due_day(client):
    token = _signup_household(client)
    client.post(
        "/wallets", json={"name": "Cash", "type": "cash", "opening_balance": 500}, headers=auth_headers(token)
    )

    fired = run_bill_due_reminders(today=date(2026, 1, 10))
    assert fired == []


def test_ignores_archived_wallets(client):
    token = _signup_household(client)
    today = date(2026, 1, 10)
    due_day = (today + timedelta(days=1)).day
    wallet_id = _credit_card(client, token, due_day)
    client.delete(f"/wallets/{wallet_id}", headers=auth_headers(token))

    fired = run_bill_due_reminders(today=today)
    assert fired == []

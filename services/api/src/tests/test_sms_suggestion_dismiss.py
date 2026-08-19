import pytest

from conftest import auth_headers, signup
from shared.sms_parser_rules_seed import seed_default_sms_parser_rules


@pytest.fixture(autouse=True)
def _seed_parser_rules():
    seed_default_sms_parser_rules()


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _ingest(client, token, sender_id="HDFCBK"):
    raw_text = "Rs.450.00 debited from A/c XX1234 at SWIGGY BANGALORE on 01-Jan-24. Avl Bal Rs.5000"
    resp = client.post("/sms/ingest", json={"raw_text": raw_text, "sender_id": sender_id}, headers=auth_headers(token))
    return resp.get_json()["data"]


def test_dismiss_sets_status_and_creates_no_transaction(client):
    token = _signup_household(client)
    sms = _ingest(client, token)

    resp = client.post(f"/sms/suggestions/{sms['id']}/dismiss", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["status"] == "dismissed"
    assert body["resolved_transaction_id"] is None

    txns = client.get("/transactions", headers=auth_headers(token)).get_json()["data"]["transactions"]
    assert txns == []

    suggestions = client.get("/sms/suggestions", headers=auth_headers(token)).get_json()["data"]["suggestions"]
    assert suggestions == []


def test_dismiss_already_resolved_suggestion_fails(client):
    token = _signup_household(client)
    sms = _ingest(client, token)
    client.post(f"/sms/suggestions/{sms['id']}/dismiss", headers=auth_headers(token))

    resp = client.post(f"/sms/suggestions/{sms['id']}/dismiss", headers=auth_headers(token))
    assert resp.status_code == 400


def test_dismiss_requires_auth(client):
    resp = client.post("/sms/suggestions/000000000000000000000000/dismiss")
    assert resp.status_code == 401


def test_dismiss_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    sms = _ingest(client, token_a)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.post(f"/sms/suggestions/{sms['id']}/dismiss", headers=auth_headers(token_b))
    assert resp.status_code == 404

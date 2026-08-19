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


def _ingest(client, token, raw_text="Rs.450.00 debited from A/c XX1234 at SWIGGY BANGALORE on 01-Jan-24. Avl Bal Rs.5000", sender_id="HDFCBK"):
    return client.post("/sms/ingest", json={"raw_text": raw_text, "sender_id": sender_id}, headers=auth_headers(token))


def test_list_suggestions_returns_only_suggested_status(client):
    token = _signup_household(client)
    _ingest(client, token)

    resp = client.get("/sms/suggestions", headers=auth_headers(token))
    assert resp.status_code == 200
    suggestions = resp.get_json()["data"]["suggestions"]
    assert len(suggestions) == 1
    assert suggestions[0]["status"] == "suggested"
    assert "raw_text" not in suggestions[0]


def test_list_suggestions_household_scoped(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    _ingest(client, token_a)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp_b = client.get("/sms/suggestions", headers=auth_headers(token_b))
    assert resp_b.get_json()["data"]["suggestions"] == []

    resp_a = client.get("/sms/suggestions", headers=auth_headers(token_a))
    assert len(resp_a.get_json()["data"]["suggestions"]) == 1


def test_list_suggestions_requires_auth(client):
    resp = client.get("/sms/suggestions")
    assert resp.status_code == 401

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


def _wallet(client, token, **overrides):
    body = {"name": "HDFC Card", "type": "bank_account", "opening_balance": 5000}
    body.update(overrides)
    return client.post("/wallets", json=body, headers=auth_headers(token)).get_json()["data"]["id"]


def _category(client, token, name="Food", type_="expense"):
    resp = client.post("/categories", json={"name": name, "type": type_}, headers=auth_headers(token))
    return resp.get_json()["data"]["id"]


def _ingest(client, token, raw_text, sender_id, received_at=None):
    body = {"raw_text": raw_text, "sender_id": sender_id}
    if received_at:
        body["received_at"] = received_at
    return client.post("/sms/ingest", json=body, headers=auth_headers(token))


def test_ingest_hdfc_sms_creates_suggestion(client):
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "Rs.450.00 debited from A/c XX1234 at SWIGGY BANGALORE on 01-Jan-24. Avl Bal Rs.5000",
        "HDFCBK",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "parsed"
    assert body["parsed_amount"] == 450.00
    assert body["parsed_direction"] == "debit"
    assert body["parsed_merchant"] == "SWIGGY BANGALORE"
    assert body["status"] == "suggested"
    assert "raw_text" not in body


def test_ingest_axis_sms_creates_suggestion(client):
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "INR 1200 debited from Card ending 5678 at AMAZON RETAIL on 02-Jan-24. Avl Bal Rs.3000",
        "AXISBK",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "parsed"
    assert body["parsed_amount"] == 1200
    assert body["parsed_direction"] == "debit"
    assert body["parsed_merchant"] == "AMAZON RETAIL"


def test_ingest_sbi_sms_credit_creates_suggestion(client):
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "Rs.2000.00 credited to A/c XX9988 from RAMA SATHYA on 03-Jan-24. Avl Bal Rs.10000",
        "SBIINB",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "parsed"
    assert body["parsed_direction"] == "credit"
    assert body["parsed_amount"] == 2000.00


def test_ingest_unrecognized_sender_and_format_fails_to_parse(client):
    token = _signup_household(client)
    resp = _ingest(client, token, "Hey, are we still on for dinner tonight?", "FRIEND1")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "failed"
    assert body["suggested_wallet_id"] is None


def test_ingest_dedup_links_existing_transaction(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, account_last4="1234")
    category_id = _category(client, token)

    client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 450},
        headers=auth_headers(token),
    )

    resp = _ingest(
        client,
        token,
        "Rs.450.00 debited from A/c XX1234 at SWIGGY BANGALORE on 01-Jan-24. Avl Bal Rs.5000",
        "HDFCBK",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["status"] == "accepted"
    assert body["resolved_transaction_id"] is not None

    # It should not show up as a pending suggestion.
    suggestions = client.get("/sms/suggestions", headers=auth_headers(token)).get_json()["data"]["suggestions"]
    assert suggestions == []


def test_ingest_missing_raw_text_fails_validation(client):
    token = _signup_household(client)
    resp = client.post("/sms/ingest", json={"sender_id": "HDFCBK"}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_ingest_missing_sender_id_fails_validation(client):
    token = _signup_household(client)
    resp = client.post("/sms/ingest", json={"raw_text": "Rs.100 debited"}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_ingest_requires_auth(client):
    resp = client.post("/sms/ingest", json={"raw_text": "Rs.100 debited", "sender_id": "HDFCBK"})
    assert resp.status_code == 401

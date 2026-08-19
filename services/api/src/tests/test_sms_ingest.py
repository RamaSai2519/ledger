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


def test_ingest_kotak_sms_creates_suggestion(client):
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "Rs.780.00 spent on Kotak Bank Card XX4321 at RELIANCE FRESH on 04-Jan-24. Avl Bal Rs.15000",
        "KOTAKB",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "parsed"
    assert body["parsed_amount"] == 780.00
    assert body["parsed_direction"] == "debit"
    assert body["parsed_merchant"] == "RELIANCE FRESH"


def test_ingest_zet_credit_card_sms_creates_suggestion(client):
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "Rs.999.00 debited from Zet Card XX6677 at NETFLIX on 05-Jan-24. Avl Bal Rs.20000",
        "ZETPAY",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "parsed"
    assert body["parsed_amount"] == 999.00
    assert body["parsed_merchant"] == "NETFLIX"


def test_ingest_amazon_pay_later_sms_creates_suggestion(client):
    # AXIO's sender_ids include AMZNPL (co-branded Amazon Pay Later), so a
    # sender of "AMZNPL" should resolve to the AXIO bank_code's rules.
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "INR 350.00 spent on Amazon Pay Later A/c XX0099 at AMAZON on 06-Jan-24. Avl Bal Rs.5000",
        "AMZNPL",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "parsed"
    assert body["parsed_amount"] == 350.00
    assert body["parsed_merchant"] == "AMAZON"


def test_ingest_jupiter_credit_card_sms_creates_suggestion(client):
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "Rs.1450.00 spent on Jupiter Card XX5566 at BIGBASKET on 07-Jan-24. Avl Bal Rs.8000",
        "JUPCC",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "parsed"
    assert body["parsed_amount"] == 1450.00
    assert body["parsed_merchant"] == "BIGBASKET"


def test_ingest_canara_sms_credit_creates_suggestion(client):
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "Rs.3000.00 credited to A/c XX7788 from EMPLOYER PVT LTD on 08-Jan-24. Avl Bal Rs.25000",
        "CANBNK",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "parsed"
    assert body["parsed_direction"] == "credit"
    assert body["parsed_amount"] == 3000.00


def test_ingest_kotak_upi_sent_wording_fails_to_parse(client):
    # A real-world QA finding from this pass: Kotak's UPI-transfer template
    # ("Sent Rs.X ... to <payee>") doesn't use any of the shared debit
    # regex's verbs (debited/spent/paid/debit), so it fails to match KOTAK's
    # bank-specific rule. It does NOT fall through to the low-confidence
    # GENERIC fallback either — find_matching_rules (shared/sms_parsing.py)
    # only tries GENERIC when no rule's sender_ids list contains this
    # sender_id at all, and KOTAKB is already claimed by the KOTAK rule set,
    # so an unmatched KOTAK message is dropped as parse_status="failed"
    # rather than degrading to a low-confidence suggestion. Documented here
    # rather than "fixed", since a real fix means adding a new bank-specific
    # pattern row (data-driven, plan.md §2.2) covering the UPI-sent wording,
    # not an app/server code change — out of scope for this QA pass, but
    # worth a follow-up ticket since UPI transfers are common.
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "Sent Rs.250.00 from Kotak Bank AC X4321 to MERCHANT UPI on 09-Jan-24 via UPI. Avl Bal Rs.14750",
        "KOTAKB",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "failed"
    assert body["parsed_merchant"] is None
    assert body["suggested_wallet_id"] is None


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

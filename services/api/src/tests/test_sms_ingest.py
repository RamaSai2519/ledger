import pytest
from bson import ObjectId

from conftest import auth_headers, signup
from shared.category_keyword_rules_seed import seed_default_category_keyword_rules
from shared.db import get_notifications_collection, get_transactions_collection, get_wallets_collection
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


def test_ingest_kotak_upi_sent_wording_parses(client):
    # LED-18 fix: Kotak's UPI-transfer template ("Sent Rs.X ... to <payee>")
    # used to fail because the old parser only matched a fixed per-bank
    # debit/credit regex whose verb list didn't include "sent", and the
    # sender's KOTAKB claim on the KOTAK bank_code meant it never fell
    # through to the GENERIC fallback either. The new layered pipeline's
    # generic extractors aren't tied to a single verb list per bank (the
    # normalizer/classifier/amount-extractor all recognize "sent" as a debit
    # verb), so this now parses like any other transactional SMS.
    token = _signup_household(client)
    resp = _ingest(
        client,
        token,
        "Sent Rs.250.00 from Kotak Bank AC X4321 to BIGBASKET on 09-Jan-24 via UPI Ref 998877. Avl Bal Rs.14750",
        "KOTAKB",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "parsed"
    assert body["parsed_amount"] == 250.00
    assert body["parsed_direction"] == "debit"
    assert body["parsed_merchant"] == "BIGBASKET"
    assert body["transaction_type"] == "upi_payment"
    assert body["parsed_ref"] == "998877"


def test_ingest_unrecognized_sender_and_format_is_not_a_transaction(client):
    # LED-18: a message with no debit/credit-shaped wording at all is
    # classified `not_transaction` (spec Part 3), distinct from `failed`
    # (which now means "recognizably transactional wording, but no amount
    # could be extracted").
    token = _signup_household(client)
    resp = _ingest(client, token, "Hey, are we still on for dinner tonight?", "FRIEND1")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parse_status"] == "not_transaction"
    assert body["suggested_wallet_id"] is None
    assert body["status"] == "not_applicable"

    # And it must never show up as a pending suggestion.
    suggestions = client.get("/sms/suggestions", headers=auth_headers(token)).get_json()["data"]["suggestions"]
    assert suggestions == []


def test_ingest_transactional_wording_without_amount_fails_to_parse(client):
    token = _signup_household(client)
    resp = _ingest(client, token, "Your account was debited successfully.", "HDFCBK")
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


def test_ingest_single_asterisk_masked_account_resolves_wallet(client):
    """LED-29 regression: HDFC's "A/C *3842" wording uses a single "*" mask
    character, not "XX"/"**" like other banks - the last4 extractor
    previously required 2+ mask chars, so this format never resolved
    parsed_last4 at all and the wallet auto-select silently fell through to
    lower-confidence layers (or nothing)."""
    token = _signup_household(client)
    _wallet(client, token, account_last4="3842")

    resp = _ingest(
        client,
        token,
        "Sent Rs.198.46\nFrom HDFC Bank A/C *3842\nTo Zomato Media Private Limi\nOn 21/08/26\n"
        "Ref 623325940843\nNot You?\nCall 18002586161/SMS BLOCK UPI to 7308080808",
        "HDFCBK",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["parsed_last4"] == "3842"
    assert body["suggested_wallet_id"] is not None
    assert body["wallet_confidence"] == 0.95


def test_ingest_dedup_matches_on_ref_even_when_wallet_resolution_fails(client):
    """LED-29 regression: dedup used to be gated entirely on wallet
    resolution succeeding (`if wallet is not None`), so any SMS whose wallet
    couldn't be resolved (e.g. an unrecognized masked-account format) would
    re-surface the same real-world transaction as a brand-new suggestion
    every time it was (re-)delivered, even though the bank's own ref/UTR
    already matched an existing transaction. A transaction_id/UTR match must
    dedupe regardless of wallet resolution."""
    token = _signup_household(client)
    wallet_id = _wallet(client, token, account_last4="3842")
    household_id = get_wallets_collection().find_one({"_id": ObjectId(wallet_id)})["household_id"]

    get_transactions_collection().insert_one(
        {
            "household_id": household_id,
            "wallet_id": ObjectId(wallet_id),
            "type": "expense",
            "amount": 198.46,
            "sms_transaction_id": "623325940843",
        }
    )

    # Same ref, but wrapped in wording the last4 extractor won't recognize
    # (no masked-account marker at all), so wallet resolution fails.
    resp = _ingest(
        client,
        token,
        "Sent Rs.198.46 from HDFC Bank To Zomato Media Private Limi On 21/08/26 Ref 623325940843",
        "HDFCBK",
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["status"] == "accepted"
    assert body["resolved_transaction_id"] is not None

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


def test_ingest_notifies_with_category_and_wallet_guess_for_notifee(client):
    """LED-21: the sms_suggestion notification payload needs the category
    guess and wallet label up front so the client's notifee-built
    notification (design s21) can show a Confirm action and the "best
    guess" line without a round trip back to the API."""
    seed_default_category_keyword_rules()
    token = _signup_household(client)
    _wallet(client, token, account_last4="1234")

    resp = _ingest(
        client,
        token,
        "Rs.450.00 debited from A/c XX1234 at SWIGGY BANGALORE on 01-Jan-24. Avl Bal Rs.5000",
        "HDFCBK",
    )
    assert resp.status_code == 200
    sms_id = resp.get_json()["data"]["id"]

    notification = get_notifications_collection().find_one({"type": "sms_suggestion"})
    assert notification is not None
    payload = notification["payload"]
    assert payload["sms_id"] == sms_id
    assert payload["merchant"] == "SWIGGY BANGALORE"
    assert payload["wallet_label"] == "HDFC Card ••1234"
    assert payload["category_name"] == "Food & Dining"
    assert payload["can_confirm"] is True

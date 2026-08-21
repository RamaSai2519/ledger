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


def _ingest(client, token, amount="450.00", sender_id="HDFCBK"):
    raw_text = f"Rs.{amount} debited from A/c XX1234 at SWIGGY BANGALORE on 01-Jan-24. Avl Bal Rs.5000"
    resp = client.post("/sms/ingest", json={"raw_text": raw_text, "sender_id": sender_id}, headers=auth_headers(token))
    return resp.get_json()["data"]


def test_accept_with_override_writes_override_to_merchant_map_and_creates_txn(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, account_last4="1234")
    category_id = _category(client, token)

    sms = _ingest(client, token, amount="450.00")
    assert sms["suggested_wallet_id"] == wallet_id
    assert sms["suggested_category_id"] is None  # no learned mapping yet

    resp = client.post(
        f"/sms/suggestions/{sms['id']}/accept",
        json={"category_id": category_id},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    txn = resp.get_json()["data"]
    assert txn["wallet_id"] == wallet_id
    assert txn["category_id"] == category_id
    assert txn["amount"] == 450.00
    assert txn["source"] == "sms_confirmed"
    assert txn["sms_id"] == sms["id"]

    wallet = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token)).get_json()["data"]
    assert wallet["current_balance"] == 5000 - 450.00

    # A second SMS for the same merchant should now get the learned category
    # suggested automatically (frequency-based learning, plan.md).
    sms2 = _ingest(client, token, amount="300.00")
    assert sms2["suggested_wallet_id"] == wallet_id
    assert sms2["suggested_category_id"] == category_id


def test_accept_with_no_override_uses_suggested_wallet_and_category(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, account_last4="1234")
    category_id = _category(client, token)

    # Seed the merchant_category_map by accepting once with an override.
    sms1 = _ingest(client, token, amount="450.00")
    client.post(f"/sms/suggestions/{sms1['id']}/accept", json={"category_id": category_id}, headers=auth_headers(token))

    sms2 = _ingest(client, token, amount="300.00")
    assert sms2["suggested_category_id"] == category_id

    resp = client.post(f"/sms/suggestions/{sms2['id']}/accept", json={}, headers=auth_headers(token))
    assert resp.status_code == 200
    txn = resp.get_json()["data"]
    assert txn["wallet_id"] == wallet_id
    assert txn["category_id"] == category_id

    wallet = client.get(f"/wallets/{wallet_id}", headers=auth_headers(token)).get_json()["data"]
    assert wallet["current_balance"] == 5000 - 450.00 - 300.00


def test_accept_already_resolved_suggestion_fails(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, account_last4="1234")
    category_id = _category(client, token)

    sms = _ingest(client, token)
    client.post(f"/sms/suggestions/{sms['id']}/accept", json={"category_id": category_id}, headers=auth_headers(token))

    resp = client.post(f"/sms/suggestions/{sms['id']}/accept", json={"category_id": category_id}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_accept_without_resolvable_wallet_or_category_fails(client):
    token = _signup_household(client)
    # Unrecognized sender + free-text -> not classified as a transaction at
    # all (LED-18), so nothing is suggested and accept must be rejected
    # without an override.
    resp = client.post(
        "/sms/ingest", json={"raw_text": "just chatting, nothing financial here", "sender_id": "FRIEND1"}, headers=auth_headers(token)
    )
    sms = resp.get_json()["data"]
    assert sms["parse_status"] == "not_transaction"

    accept_resp = client.post(f"/sms/suggestions/{sms['id']}/accept", json={}, headers=auth_headers(token))
    assert accept_resp.status_code == 400


def test_accept_requires_auth(client):
    resp = client.post("/sms/suggestions/000000000000000000000000/accept", json={})
    assert resp.status_code == 401


def test_accept_cross_household_not_found(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    _wallet(client, token_a, account_last4="1234")
    _category(client, token_a)
    sms = _ingest(client, token_a)

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.post(f"/sms/suggestions/{sms['id']}/accept", json={}, headers=auth_headers(token_b))
    assert resp.status_code == 404


def _zomato_raw_text(amount: str) -> str:
    return (
        f"Sent Rs.{amount}\nFrom HDFC Bank A/C *3842\nTo Zomato Media Private Limi\n"
        "On 21/08/26\nRef 623325940843\nNot You?\nCall 18002586161/SMS BLOCK UPI to 7308080808"
    )


def test_accept_with_merchant_name_creates_alias_and_learns_mapping(client):
    """LED-28: a picked/typed canonical merchant name on accept should (a)
    become the transaction's merchant_name instead of the raw truncated
    text, and (b) write a household merchant_aliases entry so a *later* SMS
    with the same raw variant resolves straight to the canonical
    name/category/wallet without asking again."""
    token = _signup_household(client)
    wallet_id = _wallet(client, token, account_last4="3842", name="HDFC")
    category_id = _category(client, token, name="Food")

    resp = client.post(
        "/sms/ingest", json={"raw_text": _zomato_raw_text("198.46"), "sender_id": "HDFCBK"}, headers=auth_headers(token)
    )
    sms = resp.get_json()["data"]
    assert sms["parsed_merchant"] == "Zomato Media Private Limi"
    assert sms["suggested_category_id"] is None  # no learned mapping yet

    accept_resp = client.post(
        f"/sms/suggestions/{sms['id']}/accept",
        json={"category_id": category_id, "merchant_name": "Zomato"},
        headers=auth_headers(token),
    )
    assert accept_resp.status_code == 200
    txn = accept_resp.get_json()["data"]
    assert txn["merchant_name"] == "Zomato"

    # A later SMS with the same raw truncated variant should now resolve via
    # the freshly-written alias straight to the canonical name and the
    # learned category/wallet - no merchant_name override needed this time.
    resp2 = client.post(
        "/sms/ingest", json={"raw_text": _zomato_raw_text("250.00"), "sender_id": "HDFCBK"}, headers=auth_headers(token)
    )
    sms2 = resp2.get_json()["data"]
    assert sms2["parsed_merchant"] == "Zomato Media Private Limi"
    assert sms2["merchant_normalized"] == "Zomato"
    assert sms2["suggested_category_id"] == category_id
    assert sms2["suggested_wallet_id"] == wallet_id


def test_merchant_alias_from_one_household_does_not_leak_to_another(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    _wallet(client, token_a, account_last4="3842", name="HDFC")
    category_id = _category(client, token_a, name="Food")

    sms = client.post(
        "/sms/ingest", json={"raw_text": _zomato_raw_text("198.46"), "sender_id": "HDFCBK"}, headers=auth_headers(token_a)
    ).get_json()["data"]
    client.post(
        f"/sms/suggestions/{sms['id']}/accept",
        json={"category_id": category_id, "merchant_name": "Zomato"},
        headers=auth_headers(token_a),
    )

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    _wallet(client, token_b, account_last4="3842", name="HDFC")
    sms_b = client.post(
        "/sms/ingest", json={"raw_text": _zomato_raw_text("198.46"), "sender_id": "HDFCBK"}, headers=auth_headers(token_b)
    ).get_json()["data"]
    # Household B has no learned mapping of its own - A's custom alias must
    # not leak across households.
    assert sms_b["suggested_category_id"] is None

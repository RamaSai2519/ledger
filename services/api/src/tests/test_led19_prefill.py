"""LED-19: layered wallet/category prefill for SMS suggestions."""
import pytest

from conftest import auth_headers, signup
from shared.category_keyword_rules_seed import seed_default_category_keyword_rules
from shared.merchant_aliases_seed import seed_default_merchant_aliases
from shared.sms_parser_rules_seed import seed_default_sms_parser_rules


@pytest.fixture(autouse=True)
def _seed_rules():
    seed_default_sms_parser_rules()


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def _wallet(client, token, **overrides):
    body = {"name": "Wallet", "type": "bank_account", "opening_balance": 5000}
    body.update(overrides)
    return client.post("/wallets", json=body, headers=auth_headers(token)).get_json()["data"]["id"]


def _category(client, token, name="Food", type_="expense"):
    resp = client.post("/categories", json={"name": name, "type": type_}, headers=auth_headers(token))
    return resp.get_json()["data"]["id"]


def _category_id_by_name(client, token, name, type_="expense"):
    resp = client.get(f"/categories?type={type_}", headers=auth_headers(token))
    for c in resp.get_json()["data"]["categories"]:
        if c["name"] == name:
            return c["id"]
    return None


def _ingest(client, token, merchant="SWIGGY BANGALORE", last4="9999", sender_id="HDFCBK", amount="450.00"):
    raw_text = f"Rs.{amount} debited from A/c XX{last4} at {merchant} on 01-Jan-24. Avl Bal Rs.5000"
    resp = client.post("/sms/ingest", json={"raw_text": raw_text, "sender_id": sender_id}, headers=auth_headers(token))
    return resp.get_json()["data"]


def test_institution_match_suggests_wallet_without_last4(client):
    token = _signup_household(client)
    wallet_id = _wallet(client, token, provider="HDFC Bank")

    sms = _ingest(client, token, last4="1234", sender_id="HDFCBK")
    assert sms["suggested_wallet_id"] == wallet_id
    assert sms["wallet_confidence"] == 0.7


def test_single_wallet_of_type_fallback(client):
    token = _signup_household(client)
    # No provider set, so institution matching can't fire — but there's only
    # one bank_account wallet, so the single-wallet fallback should.
    wallet_id = _wallet(client, token)

    sms = _ingest(client, token, last4="1234", sender_id="HDFCBK")
    assert sms["suggested_wallet_id"] == wallet_id
    assert sms["wallet_confidence"] == 0.5


def test_default_wallet_fallback_when_multiple_wallets_of_type(client):
    token = _signup_household(client)
    _wallet(client, token, name="Wallet A")
    wallet_b = _wallet(client, token, name="Wallet B")
    client.patch(f"/wallets/{wallet_b}", json={"is_default": True}, headers=auth_headers(token))

    sms = _ingest(client, token, last4="1234", sender_id="HDFCBK")
    assert sms["suggested_wallet_id"] == wallet_b
    assert sms["wallet_confidence"] == 0.3


def test_is_default_is_unique_per_household(client):
    token = _signup_household(client)
    wallet_a = _wallet(client, token, name="Wallet A")
    wallet_b = _wallet(client, token, name="Wallet B")

    client.patch(f"/wallets/{wallet_a}", json={"is_default": True}, headers=auth_headers(token))
    client.patch(f"/wallets/{wallet_b}", json={"is_default": True}, headers=auth_headers(token))

    wallet_a_data = client.get(f"/wallets/{wallet_a}", headers=auth_headers(token)).get_json()["data"]
    wallet_b_data = client.get(f"/wallets/{wallet_b}", headers=auth_headers(token)).get_json()["data"]
    assert wallet_a_data["is_default"] is False
    assert wallet_b_data["is_default"] is True


def test_merchant_wallet_map_learning_loop_requires_frequency_above_threshold(client):
    token = _signup_household(client)
    # Two same-type wallets with no last4/provider so last4/institution/
    # single-wallet layers all decline to guess, isolating merchant_wallet_map.
    _wallet(client, token, name="Cash A", type="cash")
    wallet_b = _wallet(client, token, name="Cash B", type="cash")
    category_id = _category(client, token)

    for i in range(2):
        sms = _ingest(client, token, merchant="LOCAL STORE", last4="0000", amount=f"{100 + i}.00")
        assert sms["suggested_wallet_id"] is None
        client.post(
            f"/sms/suggestions/{sms['id']}/accept",
            json={"wallet_id": wallet_b, "category_id": category_id},
            headers=auth_headers(token),
        )

    # frequency is now 2 (== MERCHANT_WALLET_MAP_MIN_FREQUENCY) — still not
    # trusted (decay guard: a couple of accepts shouldn't lock the mapping).
    still_unprefilled = _ingest(client, token, merchant="LOCAL STORE", last4="0000", amount="150.00")
    assert still_unprefilled["suggested_wallet_id"] is None
    client.post(
        f"/sms/suggestions/{still_unprefilled['id']}/accept",
        json={"wallet_id": wallet_b, "category_id": category_id},
        headers=auth_headers(token),
    )

    # frequency is now 3 (> threshold) — should now prefill wallet_b.
    prefilled = _ingest(client, token, merchant="LOCAL STORE", last4="0000", amount="175.00")
    assert prefilled["suggested_wallet_id"] == wallet_b
    assert prefilled["wallet_confidence"] == 0.8


def test_category_alias_fuzzy_match(client):
    seed_default_merchant_aliases()
    token = _signup_household(client)
    _wallet(client, token, account_last4="1234")
    category_id = _category(client, token, name="Food")

    seed_sms = _ingest(client, token, merchant="SWIGGY", last4="1234")
    client.post(f"/sms/suggestions/{seed_sms['id']}/accept", json={"category_id": category_id}, headers=auth_headers(token))

    # A differently-worded variant of the same canonical merchant (per
    # merchant_aliases_seed.py's "Swiggy" group) should still fuzzy-match via
    # the aliases layer 2, not just the exact layer 1.
    fuzzy_sms = _ingest(client, token, merchant="SWIGGY BANGALORE", last4="1234")
    assert fuzzy_sms["suggested_category_id"] == category_id
    assert fuzzy_sms["category_confidence"] == 0.75


def test_category_keyword_heuristic(client):
    seed_default_category_keyword_rules()
    token = _signup_household(client)
    _wallet(client, token, account_last4="1234")
    travel_category_id = _category_id_by_name(client, token, "Travel")
    assert travel_category_id  # seeded automatically at household creation

    sms = _ingest(client, token, merchant="IRCTC", last4="1234")
    assert sms["suggested_category_id"] == travel_category_id
    assert sms["category_confidence"] == 0.6


def test_no_category_match_leaves_suggestion_null(client):
    token = _signup_household(client)
    _wallet(client, token, account_last4="1234")

    sms = _ingest(client, token, merchant="UNKNOWN MERCHANT XYZ", last4="1234")
    assert sms["suggested_category_id"] is None
    assert sms["category_confidence"] == 0.0

from conftest import auth_headers, signup
from shared.merchant_aliases_seed import seed_default_merchant_aliases
from shared.sms_parser_rules_seed import seed_default_sms_parser_rules


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def test_merchants_list_returns_seeded_global_names(client):
    seed_default_merchant_aliases()
    token = _signup_household(client)

    resp = client.get("/merchants", headers=auth_headers(token))
    assert resp.status_code == 200
    names = resp.get_json()["data"]["merchants"]
    assert "Zomato" in names
    assert "Swiggy" in names
    assert names == sorted(names)


def test_merchants_list_filters_by_q(client):
    seed_default_merchant_aliases()
    token = _signup_household(client)

    resp = client.get("/merchants?q=zom", headers=auth_headers(token))
    assert resp.status_code == 200
    names = resp.get_json()["data"]["merchants"]
    assert names == ["Zomato"]


def test_merchants_list_requires_auth(client):
    resp = client.get("/merchants")
    assert resp.status_code == 401


def test_merchants_list_blank_q_rejected(client):
    token = _signup_household(client)
    resp = client.get("/merchants?q=%20", headers=auth_headers(token))
    assert resp.status_code == 400


def test_merchants_list_includes_household_specific_alias_but_not_other_households(client):
    seed_default_sms_parser_rules()
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    client.post("/wallets", json={"name": "HDFC", "type": "bank_account", "opening_balance": 0, "account_last4": "3842"}, headers=auth_headers(token_a))
    category_id = client.post("/categories", json={"name": "Food", "type": "expense"}, headers=auth_headers(token_a)).get_json()["data"]["id"]

    raw_text = (
        "Sent Rs.198.46\nFrom HDFC Bank A/C *3842\nTo Zomato Media Private Limi\n"
        "On 21/08/26\nRef 623325940843\nNot You?\nCall 18002586161/SMS BLOCK UPI to 7308080808"
    )
    sms = client.post("/sms/ingest", json={"raw_text": raw_text, "sender_id": "HDFCBK"}, headers=auth_headers(token_a)).get_json()["data"]
    client.post(
        f"/sms/suggestions/{sms['id']}/accept",
        json={"category_id": category_id, "merchant_name": "My Local Zomato Branch"},
        headers=auth_headers(token_a),
    )

    resp_a = client.get("/merchants?q=local", headers=auth_headers(token_a))
    assert resp_a.get_json()["data"]["merchants"] == ["My Local Zomato Branch"]

    token_b = _signup_household(client, mobile_number="9111111111", name="B")
    resp_b = client.get("/merchants?q=local", headers=auth_headers(token_b))
    assert resp_b.get_json()["data"]["merchants"] == []

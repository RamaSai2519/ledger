from conftest import auth_headers, signup
from shared.sms_parser_rules_seed import seed_default_sms_parser_rules


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def test_create_parser_rule_is_household_scoped(client):
    token = _signup_household(client)
    resp = client.post(
        "/sms/parser-rules",
        json={
            "bank_code": "MYBANK",
            "sender_ids": ["MYBANK1"],
            "patterns": [{"regex": r"Rs\.(?P<amount>[\d.]+) debited", "txn_type": "debit"}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["bank_code"] == "MYBANK"
    assert body["household_id"] is not None


def test_create_parser_rule_invalid_regex_fails(client):
    token = _signup_household(client)
    resp = client.post(
        "/sms/parser-rules",
        json={
            "bank_code": "MYBANK",
            "sender_ids": ["MYBANK1"],
            "patterns": [{"regex": "Rs.(unclosed", "txn_type": "debit"}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


def test_create_parser_rule_missing_sender_ids_fails(client):
    token = _signup_household(client)
    resp = client.post(
        "/sms/parser-rules",
        json={"bank_code": "MYBANK", "sender_ids": [], "patterns": [{"regex": r"Rs\.(?P<amount>[\d.]+)"}]},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


def test_create_parser_rule_requires_auth(client):
    resp = client.post(
        "/sms/parser-rules",
        json={"bank_code": "MYBANK", "sender_ids": ["X"], "patterns": [{"regex": r"Rs\.(?P<amount>[\d.]+)"}]},
    )
    assert resp.status_code == 401


def test_list_parser_rules_returns_household_and_global_rules(client):
    seed_default_sms_parser_rules()
    token = _signup_household(client)
    client.post(
        "/sms/parser-rules",
        json={
            "bank_code": "MYBANK",
            "sender_ids": ["MYBANK1"],
            "patterns": [{"regex": r"Rs\.(?P<amount>[\d.]+) debited", "txn_type": "debit"}],
        },
        headers=auth_headers(token),
    )

    resp = client.get("/sms/parser-rules", headers=auth_headers(token))
    assert resp.status_code == 200
    rules = resp.get_json()["data"]["rules"]
    bank_codes = {r["bank_code"] for r in rules}

    # Global seed rules (household_id=None) plus the household's own custom rule.
    assert "MYBANK" in bank_codes
    assert "HDFC" in bank_codes
    assert "GENERIC" in bank_codes

    mybank_rule = next(r for r in rules if r["bank_code"] == "MYBANK")
    assert mybank_rule["household_id"] is not None
    hdfc_rule = next(r for r in rules if r["bank_code"] == "HDFC")
    assert hdfc_rule["household_id"] is None


def test_list_parser_rules_requires_auth(client):
    resp = client.get("/sms/parser-rules")
    assert resp.status_code == 401

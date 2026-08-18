from bson import ObjectId
from conftest import auth_headers, signup

from shared.db import get_users_collection


def _signup(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    data = resp.get_json()["data"]
    return data["access_token"], data["user_id"]


def test_register_fcm_token_success(client):
    token, user_id = _signup(client)
    resp = client.post("/users/fcm-token", json={"token": "device-token-1"}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["registered"] is True

    user = get_users_collection().find_one({"_id": ObjectId(user_id)})
    assert user["fcm_tokens"] == ["device-token-1"]


def test_register_fcm_token_dedupes(client):
    token, user_id = _signup(client)
    client.post("/users/fcm-token", json={"token": "device-token-1"}, headers=auth_headers(token))
    client.post("/users/fcm-token", json={"token": "device-token-1"}, headers=auth_headers(token))
    client.post("/users/fcm-token", json={"token": "device-token-2"}, headers=auth_headers(token))

    user = get_users_collection().find_one({"_id": ObjectId(user_id)})
    assert sorted(user["fcm_tokens"]) == ["device-token-1", "device-token-2"]


def test_register_fcm_token_missing_token(client):
    token, _ = _signup(client)
    resp = client.post("/users/fcm-token", json={}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_register_fcm_token_blank_token(client):
    token, _ = _signup(client)
    resp = client.post("/users/fcm-token", json={"token": "  "}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_register_fcm_token_requires_auth(client):
    resp = client.post("/users/fcm-token", json={"token": "device-token-1"})
    assert resp.status_code == 401

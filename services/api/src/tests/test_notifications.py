from datetime import datetime, timezone

from bson import ObjectId
from conftest import auth_headers, signup

from shared.db import get_notifications_collection


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    data = resp.get_json()["data"]
    token = data["access_token"]
    user_id = data["user_id"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token, user_id


def _insert_notification(household_id, user_id, notif_type="digest", is_read=False, created_at=None):
    doc = {
        "household_id": ObjectId(household_id),
        "user_id": ObjectId(user_id),
        "type": notif_type,
        "payload": {"foo": "bar"},
        "is_read": is_read,
        "created_at": created_at or datetime.now(timezone.utc),
    }
    result = get_notifications_collection().insert_one(doc)
    return str(result.inserted_id)


def _household_id(client, token):
    return client.get("/auth/household/invite-code", headers=auth_headers(token)).get_json()["data"]["household_id"]


def test_list_notifications_requires_auth(client):
    resp = client.get("/notifications")
    assert resp.status_code == 401


def test_list_notifications_empty(client):
    token, _ = _signup_household(client)
    resp = client.get("/notifications", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["notifications"] == []


def test_list_notifications_newest_first(client):
    token, user_id = _signup_household(client)
    household_id = _household_id(client, token)

    _insert_notification(
        household_id, user_id, notif_type="digest", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    _insert_notification(
        household_id, user_id, notif_type="bill_due", created_at=datetime(2026, 1, 2, tzinfo=timezone.utc)
    )

    resp = client.get("/notifications", headers=auth_headers(token))
    body = resp.get_json()["data"]
    assert body["total"] == 2
    assert [n["type"] for n in body["notifications"]] == ["bill_due", "digest"]


def test_notifications_household_scoped(client):
    token_a, user_id_a = _signup_household(client, mobile_number="9876543210", name="A")
    household_id_a = _household_id(client, token_a)
    _insert_notification(household_id_a, user_id_a)

    token_b, _ = _signup_household(client, mobile_number="9111111111", name="B")
    resp_b = client.get("/notifications", headers=auth_headers(token_b))
    assert resp_b.get_json()["data"]["notifications"] == []


def test_mark_notification_read(client):
    token, user_id = _signup_household(client)
    household_id = _household_id(client, token)
    notif_id = _insert_notification(household_id, user_id)

    resp = client.post(f"/notifications/{notif_id}/read", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["is_read"] is True

    list_resp = client.get("/notifications", headers=auth_headers(token))
    assert list_resp.get_json()["data"]["notifications"][0]["is_read"] is True


def test_mark_notification_read_cross_household_not_found(client):
    token_a, user_id_a = _signup_household(client, mobile_number="9876543210", name="A")
    household_id_a = _household_id(client, token_a)
    notif_id = _insert_notification(household_id_a, user_id_a)

    token_b, _ = _signup_household(client, mobile_number="9111111111", name="B")
    resp = client.post(f"/notifications/{notif_id}/read", headers=auth_headers(token_b))
    assert resp.status_code == 404


def test_mark_notification_read_not_found(client):
    token, _ = _signup_household(client)
    resp = client.post("/notifications/000000000000000000000000/read", headers=auth_headers(token))
    assert resp.status_code == 404

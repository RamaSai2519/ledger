"""Shared notification fan-out: writes one `notifications` doc per household
member (so each partner has their own read/unread state on a shared event)
and attempts a single FCM multicast push across all members' devices.

Used by jobs/budget_threshold_check.py, jobs/digest_notifications.py, and
jobs/bill_due_reminders.py so the "create in-app doc(s) + best-effort push"
pattern lives in one place.
"""
from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_households_collection, get_notifications_collection, get_users_collection
from shared.fcm import send_push


def get_household_members(household_id: ObjectId) -> list[dict]:
    household = get_households_collection().find_one({"_id": household_id})
    if not household:
        return []
    member_ids = household.get("member_ids", [])
    return list(get_users_collection().find({"_id": {"$in": member_ids}}))


def notify_household(
    household_id: ObjectId,
    notification_type: str,
    payload: dict,
    title: str,
    body: str,
    *,
    push_data_only: bool = False,
) -> list[dict]:
    """Creates one notification doc per household member and best-effort
    pushes to every registered device across the household. Returns the
    inserted notification docs.

    `push_data_only=True` (LED-21) forwards `payload` into the FCM `data`
    map (stringified) instead of only `{"type": ...}`, and sends the push
    with no `notification` block — for callers whose client-side rendering
    needs the full payload up front (e.g. a rich actionable notification),
    not just enough to invalidate a query on tap."""
    members = get_household_members(household_id)
    now = datetime.now(timezone.utc)
    notifications = get_notifications_collection()

    docs = []
    all_tokens: list[str] = []
    for member in members:
        doc = {
            "household_id": household_id,
            "user_id": member["_id"],
            "type": notification_type,
            "payload": payload,
            "is_read": False,
            "created_at": now,
        }
        result = notifications.insert_one(doc)
        doc["_id"] = result.inserted_id
        docs.append(doc)
        all_tokens.extend(member.get("fcm_tokens", []) or [])

    if push_data_only:
        data = {"type": notification_type}
        data.update({k: v for k, v in payload.items() if v is not None})
        send_push(all_tokens, title, body, data=data, data_only=True)
    else:
        send_push(all_tokens, title, body, data={"type": notification_type})
    return docs

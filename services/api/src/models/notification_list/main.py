from bson import ObjectId

from shared.db import get_notifications_collection
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_notification

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def process(user_id: str, query_args: dict | None = None):
    query_args = query_args or {}
    household_id = require_household_id(user_id)

    query = {"household_id": household_id}
    # Notifications are household-scoped by default (both partners see the
    # same shared data per CLAUDE.md), but a caller may narrow to just their
    # own via user_id=me — useful for a personal inbox badge count.
    if query_args.get("user_id") == "me":
        query["user_id"] = ObjectId(user_id)
    if query_args.get("is_read") is not None:
        query["is_read"] = query_args["is_read"].lower() == "true"

    try:
        page = max(1, int(query_args.get("page", 1)))
        page_size = min(MAX_PAGE_SIZE, max(1, int(query_args.get("page_size", DEFAULT_PAGE_SIZE))))
    except ValueError:
        page, page_size = 1, DEFAULT_PAGE_SIZE

    collection = get_notifications_collection()
    total = collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    notifications = [serialize_notification(n) for n in cursor]

    return success(
        {
            "notifications": notifications,
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": page * page_size < total,
        }
    )

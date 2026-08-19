from bson import ObjectId

from models.notification_list import validate
from shared.db import get_notifications_collection
from shared.interfaces import NotificationListInput as Input
from shared.output import success
from shared.pagination import parse_pagination
from shared.scope import require_household_id
from shared.serializers import serialize_notification


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.requesting_user_id)

    mongo_query = {"household_id": household_id}
    # Notifications are household-scoped by default (both partners see the
    # same shared data per CLAUDE.md), but a caller may narrow to just their
    # own via user_id=me — useful for a personal inbox badge count.
    if inp.user_id == "me":
        mongo_query["user_id"] = ObjectId(inp.requesting_user_id)
    if inp.is_read is not None:
        mongo_query["is_read"] = inp.is_read.lower() == "true"

    page, page_size = parse_pagination(inp)

    collection = get_notifications_collection()
    total = collection.count_documents(mongo_query)
    cursor = collection.find(mongo_query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
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

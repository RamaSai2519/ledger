from bson import ObjectId

from shared.db import get_notifications_collection
from shared.interfaces import NotificationReadInput as Input
from shared.output import NotFoundError, ValidationError, success
from shared.scope import require_household_id
from shared.serializers import serialize_notification


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    try:
        oid = ObjectId(inp.notification_id)
    except Exception as exc:
        raise ValidationError("invalid_notification_id") from exc

    collection = get_notifications_collection()
    notification = collection.find_one({"_id": oid, "household_id": household_id})
    if not notification:
        raise NotFoundError("notification_not_found")

    collection.update_one({"_id": notification["_id"]}, {"$set": {"is_read": True}})
    notification["is_read"] = True
    return success(serialize_notification(notification))

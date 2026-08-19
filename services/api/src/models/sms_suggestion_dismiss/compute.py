from datetime import datetime, timezone

from shared.db import get_sms_inbox_collection


def dismiss_suggestion(sms: dict) -> dict:
    updates = {"status": "dismissed", "updated_at": datetime.now(timezone.utc)}
    get_sms_inbox_collection().update_one({"_id": sms["_id"]}, {"$set": updates})
    sms.update(updates)
    return sms

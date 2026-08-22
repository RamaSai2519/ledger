from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_users_collection
from shared.output import NotFoundError


def update_profile(user_id: str, updates: dict) -> dict:
    users = get_users_collection()
    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise NotFoundError("user_not_found")

    if "name" in updates:
        updates["name"] = updates["name"].strip()
    updates["updated_at"] = datetime.now(timezone.utc)

    users.update_one({"_id": user["_id"]}, {"$set": updates})
    user.update(updates)
    return user

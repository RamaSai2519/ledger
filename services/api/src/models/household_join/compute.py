from datetime import datetime, timezone

from bson import ObjectId

from shared.constants import MAX_HOUSEHOLD_MEMBERS
from shared.db import get_households_collection, get_users_collection
from shared.output import ConflictError, NotFoundError


def join_household(inp, user_id: str) -> dict:
    users = get_users_collection()
    households = get_households_collection()

    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise NotFoundError("user_not_found")
    if user.get("household_id"):
        raise ConflictError("already_in_a_household")

    household = households.find_one({"invite_code": inp.invite_code.upper()})
    if not household:
        raise NotFoundError("invalid_invite_code")
    if len(household["member_ids"]) >= MAX_HOUSEHOLD_MEMBERS:
        raise ConflictError("household_full")

    now = datetime.now(timezone.utc)
    households.update_one({"_id": household["_id"]}, {"$push": {"member_ids": ObjectId(user_id)}})
    users.update_one({"_id": ObjectId(user_id)}, {"$set": {"household_id": household["_id"], "updated_at": now}})

    household["member_ids"].append(ObjectId(user_id))
    return household

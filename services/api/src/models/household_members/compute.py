from bson import ObjectId

from shared.db import get_households_collection, get_users_collection
from shared.output import NotFoundError


def list_members(user_id: str) -> list[dict]:
    user = get_users_collection().find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("household_id"):
        raise NotFoundError("not_in_a_household")

    household = get_households_collection().find_one({"_id": user["household_id"]})
    if not household:
        raise NotFoundError("household_not_found")

    users_by_id = {
        u["_id"]: u for u in get_users_collection().find({"_id": {"$in": household["member_ids"]}})
    }
    # member_ids is already in join order (appended to on each join) — this
    # is the one place that order is meaningful, since it's also how
    # DEFAULT_ACCENT_PALETTE was assigned.
    return [users_by_id[member_id] for member_id in household["member_ids"] if member_id in users_by_id]

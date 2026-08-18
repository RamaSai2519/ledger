from bson import ObjectId

from shared.db import get_households_collection, get_users_collection
from shared.output import NotFoundError, success


def process(user_id: str):
    user = get_users_collection().find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("household_id"):
        raise NotFoundError("not_in_a_household")

    household = get_households_collection().find_one({"_id": user["household_id"]})
    if not household:
        raise NotFoundError("household_not_found")

    return success({"invite_code": household["invite_code"], "household_id": str(household["_id"])})

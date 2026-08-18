from shared.db import get_categories_collection, get_transactions_collection
from shared.output import ConflictError, success
from shared.scope import get_household_category, require_household_id
from shared.system_categories import is_system_category


def process(category_id: str, user_id: str):
    household_id = require_household_id(user_id)
    category = get_household_category(household_id, category_id)

    if is_system_category(category):
        raise ConflictError("cannot_delete_system_category")

    referenced = get_transactions_collection().find_one({"category_id": category["_id"]})
    if referenced:
        get_categories_collection().update_one(
            {"_id": category["_id"]}, {"$set": {"is_archived": True}}
        )
        return success({"id": str(category["_id"]), "is_archived": True, "hard_deleted": False})

    get_categories_collection().delete_one({"_id": category["_id"]})
    return success({"id": str(category["_id"]), "hard_deleted": True})

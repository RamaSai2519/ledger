from models.category_update import validate
from shared.db import get_categories_collection
from shared.output import ConflictError, success
from shared.scope import get_household_category, require_household_id
from shared.serializers import serialize_category
from shared.system_categories import is_system_category


def process(category_id: str, request_json: dict, user_id: str):
    household_id = require_household_id(user_id)
    category = get_household_category(household_id, category_id)
    updates = validate.validate(request_json)

    if is_system_category(category) and ("name" in updates or updates.get("is_archived") is True):
        # The Balance Adjustment category backs the reconcile flow — it must
        # always exist, under its known name, and never be archived out from
        # under the balance engine.
        raise ConflictError("cannot_modify_system_category")

    get_categories_collection().update_one({"_id": category["_id"]}, {"$set": updates})
    category.update(updates)
    return success(serialize_category(category))

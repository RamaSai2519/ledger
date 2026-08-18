from shared.db import get_categories_collection
from shared.output import ConflictError
from shared.scope import require_household_id


def create_category(inp, user_id: str) -> dict:
    household_id = require_household_id(user_id)
    categories = get_categories_collection()

    name = inp.name.strip()
    if categories.find_one({"household_id": household_id, "name": name, "is_archived": {"$ne": True}}):
        raise ConflictError("category_name_already_exists")

    doc = {
        "household_id": household_id,
        "name": name,
        "type": inp.type,
        "icon": inp.icon,
        "color": inp.color,
        "is_default": False,
        "is_archived": False,
    }
    result = categories.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

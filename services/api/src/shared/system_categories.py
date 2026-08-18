from bson import ObjectId

from shared.constants import SYSTEM_CATEGORY_NAMES
from shared.db import get_categories_collection

BALANCE_ADJUSTMENT_CATEGORY_NAME = "Balance Adjustment"


def get_or_create_balance_adjustment_category(household_id: ObjectId) -> dict:
    """LED-3 already seeds this per household at household-create time, but
    reconcile lazily creates it too in case a household predates that seed
    (or the category was somehow removed) — reconcile must never fail for
    lack of a system category to attach its adjustment transaction to."""
    categories = get_categories_collection()
    category = categories.find_one({"household_id": household_id, "name": BALANCE_ADJUSTMENT_CATEGORY_NAME})
    if category:
        return category

    doc = {
        "household_id": household_id,
        "name": BALANCE_ADJUSTMENT_CATEGORY_NAME,
        "type": "expense",
        "is_default": True,
        "is_archived": False,
    }
    result = categories.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def is_system_category(category: dict) -> bool:
    return category.get("name") in SYSTEM_CATEGORY_NAMES

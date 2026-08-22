from datetime import datetime, timezone

from bson import ObjectId

from shared.auth_utils import generate_invite_code
from shared.constants import DEFAULT_ACCENT_PALETTE, DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES
from shared.db import get_categories_collection, get_households_collection, get_users_collection
from shared.output import ConflictError, NotFoundError


def _unique_invite_code(households) -> str:
    for _ in range(10):
        code = generate_invite_code()
        if not households.find_one({"invite_code": code}):
            return code
    raise RuntimeError("could_not_generate_unique_invite_code")


def _seed_default_categories(household_id: ObjectId) -> None:
    categories = get_categories_collection()
    docs = [
        {"household_id": household_id, "name": name, "icon": icon, "type": "expense", "is_default": True, "is_archived": False}
        for name, icon in DEFAULT_EXPENSE_CATEGORIES
    ] + [
        {"household_id": household_id, "name": name, "icon": icon, "type": "income", "is_default": True, "is_archived": False}
        for name, icon in DEFAULT_INCOME_CATEGORIES
    ]
    for i, doc in enumerate(docs):
        doc["sort_order"] = i
    categories.insert_many(docs)


def create_household(inp, user_id: str) -> dict:
    users = get_users_collection()
    households = get_households_collection()

    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise NotFoundError("user_not_found")
    if user.get("household_id"):
        raise ConflictError("already_in_a_household")

    now = datetime.now(timezone.utc)
    household_doc = {
        "name": inp.name.strip(),
        "member_ids": [ObjectId(user_id)],
        "invite_code": _unique_invite_code(households),
        "created_at": now,
    }
    result = households.insert_one(household_doc)
    household_doc["_id"] = result.inserted_id

    users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"household_id": household_doc["_id"], "accent_color": DEFAULT_ACCENT_PALETTE[0], "updated_at": now}},
    )
    _seed_default_categories(household_doc["_id"])

    return household_doc

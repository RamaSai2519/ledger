from bson import ObjectId

from shared.db import get_categories_collection, get_transactions_collection, get_users_collection
from shared.output import NotFoundError, ValidationError


def require_household_id(user_id: str) -> ObjectId:
    """Looks up the requesting user's household_id — the household-scoping
    anchor for every wallet/category/transaction endpoint. Never trust a
    household_id passed in a request body; always derive it from the JWT
    subject's user doc so one household can never read/write another's data.
    """
    user = get_users_collection().find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("household_id"):
        raise NotFoundError("not_in_a_household")
    return user["household_id"]


def get_household_category(household_id: ObjectId, category_id: str) -> dict:
    try:
        oid = ObjectId(category_id)
    except Exception as exc:
        raise ValidationError("invalid_category_id") from exc
    category = get_categories_collection().find_one({"_id": oid, "household_id": household_id})
    if not category:
        raise NotFoundError("category_not_found")
    return category


def get_household_transaction(household_id: ObjectId, transaction_id: str) -> dict:
    try:
        oid = ObjectId(transaction_id)
    except Exception as exc:
        raise ValidationError("invalid_transaction_id") from exc
    txn = get_transactions_collection().find_one({"_id": oid, "household_id": household_id})
    if not txn:
        raise NotFoundError("transaction_not_found")
    return txn

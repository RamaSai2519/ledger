from datetime import datetime, timezone

from bson import ObjectId

from shared.output import ValidationError
from shared.scope import get_household_category
from shared.transactions_engine import get_household_wallet, update_single_wallet_transaction


def update_transaction(household_id: ObjectId, existing_txn: dict, updates: dict) -> dict:
    updates = dict(updates)

    wallet = get_household_wallet(household_id, str(updates.get("wallet_id") or existing_txn["wallet_id"]))

    if "category_id" in updates:
        category = get_household_category(household_id, updates["category_id"])
        if category.get("is_archived"):
            raise ValidationError("category_is_archived")
        if category["type"] != existing_txn["type"]:
            raise ValidationError("category_type_mismatch")
        updates["category_id"] = category["_id"]

    if "wallet_id" in updates:
        updates["wallet_id"] = wallet["_id"]

    if "date" in updates and updates["date"]:
        updates["date"] = datetime.fromisoformat(updates["date"])

    updates["updated_at"] = datetime.now(timezone.utc)

    return update_single_wallet_transaction(existing_txn, wallet, updates)

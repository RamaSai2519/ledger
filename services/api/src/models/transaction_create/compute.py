from datetime import datetime, timezone

from bson import ObjectId

from shared.output import ValidationError
from shared.scope import get_household_category, require_household_id
from shared.transactions_engine import create_single_wallet_transaction, get_household_wallet


def create_transaction(inp, user_id: str) -> dict:
    household_id = require_household_id(user_id)
    wallet = get_household_wallet(household_id, inp.wallet_id)
    category = get_household_category(household_id, inp.category_id)

    if category.get("is_archived"):
        raise ValidationError("category_is_archived")
    if category["type"] != inp.type:
        raise ValidationError("category_type_mismatch")

    now = datetime.now(timezone.utc)
    date = datetime.fromisoformat(inp.date) if inp.date else now

    doc = {
        "household_id": household_id,
        "wallet_id": wallet["_id"],
        "category_id": category["_id"],
        "user_id": ObjectId(user_id),
        "type": inp.type,
        "amount": inp.amount,
        "transfer_to_wallet_id": None,
        "merchant_name": inp.merchant_name,
        "note": inp.note,
        "date": date,
        "source": "manual",
        "sms_id": None,
        "recurring_rule_id": None,
        "created_at": now,
        "updated_at": now,
    }
    return create_single_wallet_transaction(household_id, wallet, doc)

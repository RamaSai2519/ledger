from datetime import datetime, timezone

from shared.db import get_recurring_rules_collection
from shared.output import ValidationError
from shared.scope import get_household_category, require_household_id
from shared.transactions_engine import get_household_wallet


def create_recurring_rule(inp, user_id: str) -> dict:
    household_id = require_household_id(user_id)
    wallet = get_household_wallet(household_id, inp.wallet_id)
    category = get_household_category(household_id, inp.category_id)

    if category.get("is_archived"):
        raise ValidationError("category_is_archived")
    if category["type"] != inp.type:
        raise ValidationError("category_type_mismatch")

    now = datetime.now(timezone.utc)
    # Stored naive (matching how transaction_create parses date-only ISO
    # strings) so it compares cleanly against the naive `today` that
    # jobs/recurring_transactions_check.py queries with.
    next_due_date = datetime.fromisoformat(inp.next_due_date).replace(tzinfo=None)

    doc = {
        "household_id": household_id,
        "wallet_id": wallet["_id"],
        "category_id": category["_id"],
        "type": inp.type,
        "merchant_name": inp.merchant_name,
        "amount": inp.amount,
        "frequency": inp.frequency,
        "next_due_date": next_due_date,
        "auto_detected": False,
        "auto_create": bool(inp.auto_create),
        "is_active": bool(inp.is_active),
        "created_at": now,
        "updated_at": now,
    }
    result = get_recurring_rules_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

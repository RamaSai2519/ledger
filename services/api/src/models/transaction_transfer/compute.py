from datetime import datetime, timezone

from bson import ObjectId

from shared.transactions_engine import create_transfer_transaction, get_household_wallet


def create_transfer(inp, user_id: str, household_id) -> dict:
    source = get_household_wallet(household_id, inp.wallet_id)
    dest = get_household_wallet(household_id, inp.transfer_to_wallet_id)

    now = datetime.now(timezone.utc)
    date = datetime.fromisoformat(inp.date) if inp.date else now

    doc = {
        "household_id": household_id,
        "user_id": ObjectId(user_id),
        "amount": inp.amount,
        "merchant_name": None,
        "note": inp.note,
        "date": date,
        "source": "manual",
        "sms_id": None,
        "recurring_rule_id": None,
        "created_at": now,
        "updated_at": now,
    }
    return create_transfer_transaction(household_id, source, dest, doc)

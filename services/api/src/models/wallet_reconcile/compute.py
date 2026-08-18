from datetime import datetime, timezone

from bson import ObjectId

from shared.system_categories import get_or_create_balance_adjustment_category
from shared.transactions_engine import create_single_wallet_transaction


def reconcile_wallet(household_id: ObjectId, wallet: dict, actual_balance: float, user_id: str) -> dict:
    delta = actual_balance - wallet.get("current_balance", 0)
    category = get_or_create_balance_adjustment_category(household_id)
    now = datetime.now(timezone.utc)

    doc = {
        "household_id": household_id,
        "wallet_id": wallet["_id"],
        "category_id": category["_id"],
        "user_id": ObjectId(user_id),
        "type": "adjustment",
        "amount": delta,  # signed: reconcile can move the balance either way
        "transfer_to_wallet_id": None,
        "merchant_name": None,
        "note": "Balance reconcile",
        "date": now,
        "source": "manual",
        "sms_id": None,
        "recurring_rule_id": None,
        "created_at": now,
        "updated_at": now,
    }
    txn = create_single_wallet_transaction(household_id, wallet, doc)
    wallet["current_balance"] = wallet.get("current_balance", 0) + delta
    return {"transaction": txn, "delta": delta, "wallet": wallet}

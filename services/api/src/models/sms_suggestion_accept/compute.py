from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_merchant_category_map_collection, get_sms_inbox_collection
from shared.output import ValidationError
from shared.scope import get_household_category
from shared.sms_parsing import normalize_merchant
from shared.transactions_engine import create_single_wallet_transaction, get_household_wallet

_DIRECTION_TO_TYPE = {"debit": "expense", "credit": "income"}


def _resolve_type(inp, sms: dict) -> str:
    if inp.type:
        return inp.type
    return _DIRECTION_TO_TYPE.get(sms.get("parsed_direction"), "expense")


def _resolve_wallet(inp, sms: dict, household_id: ObjectId) -> dict:
    wallet_id = inp.wallet_id or str(sms["suggested_wallet_id"])
    return get_household_wallet(household_id, wallet_id)


def _resolve_category(inp, sms: dict, household_id: ObjectId) -> dict:
    category_id = inp.category_id or str(sms["suggested_category_id"])
    return get_household_category(household_id, category_id)


def _update_merchant_category_map(household_id: ObjectId, sms: dict, category_id: ObjectId, wallet_id: ObjectId, now: datetime) -> None:
    merchant_pattern = normalize_merchant(sms.get("parsed_merchant"))
    if not merchant_pattern:
        return
    get_merchant_category_map_collection().update_one(
        {"household_id": household_id, "merchant_pattern": merchant_pattern},
        {
            "$set": {"category_id": category_id, "wallet_id": wallet_id, "updated_at": now},
            "$inc": {"frequency": 1},
            "$setOnInsert": {"household_id": household_id, "merchant_pattern": merchant_pattern, "created_at": now},
        },
        upsert=True,
    )


def accept_suggestion(sms: dict, inp, household_id: ObjectId, user_id: str) -> dict:
    txn_type = _resolve_type(inp, sms)
    wallet = _resolve_wallet(inp, sms, household_id)
    category = _resolve_category(inp, sms, household_id)

    if category.get("is_archived"):
        raise ValidationError("category_is_archived")
    if category["type"] != txn_type:
        raise ValidationError("category_type_mismatch")

    now = datetime.now(timezone.utc)
    amount = inp.amount if inp.amount is not None else sms.get("parsed_amount")
    date = datetime.fromisoformat(inp.date) if inp.date else (sms.get("received_at") or now)

    doc = {
        "household_id": household_id,
        "wallet_id": wallet["_id"],
        "category_id": category["_id"],
        "user_id": ObjectId(user_id),
        "type": txn_type,
        "amount": amount,
        "transfer_to_wallet_id": None,
        "merchant_name": sms.get("parsed_merchant"),
        "note": None,
        "date": date,
        "source": "sms_confirmed",
        "sms_id": sms["_id"],
        # LED-18: lets a *later* SMS for the same real-world transaction
        # (e.g. bank + UPI-app double notification) dedup by transaction ID
        # via shared.sms_parsing.find_dedup_transaction instead of only the
        # amount+day heuristic.
        "sms_transaction_id": sms.get("parsed_ref"),
        "recurring_rule_id": None,
        "created_at": now,
        "updated_at": now,
    }
    txn = create_single_wallet_transaction(household_id, wallet, doc)

    _update_merchant_category_map(household_id, sms, category["_id"], wallet["_id"], now)

    get_sms_inbox_collection().update_one(
        {"_id": sms["_id"]},
        {"$set": {"status": "accepted", "resolved_transaction_id": txn["_id"], "updated_at": now}},
    )

    return txn

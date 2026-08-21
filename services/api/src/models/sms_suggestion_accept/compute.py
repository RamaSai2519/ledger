from datetime import datetime, timezone

from bson import ObjectId

from shared.db import (
    get_merchant_alias_collection,
    get_merchant_category_map_collection,
    get_merchant_wallet_map_collection,
    get_sms_inbox_collection,
)
from shared.output import ValidationError
from shared.scope import get_household_category
from shared.sms.merchant_normalizer import normalize_key
from shared.sms_parsing import aliases_for_merchant, normalize_merchant
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


def _resolve_merchant_name(inp, sms: dict) -> str | None:
    """LED-28: a picked-existing or freshly-typed canonical name from the
    accept request wins over whatever raw text the parser extracted."""
    if inp.merchant_name and inp.merchant_name.strip():
        return inp.merchant_name.strip()
    return sms.get("parsed_merchant")


def _write_merchant_alias(household_id: ObjectId, sms: dict, canonical_name: str, now: datetime) -> None:
    """LED-28: when the user picked/typed a canonical name that differs from
    the parser's raw extraction, remember raw -> canonical for this
    household so the *next* SMS for the same real merchant (even a
    differently bank-truncated raw variant) resolves to it automatically via
    MerchantNormalizer, instead of asking again every time."""
    raw_merchant = sms.get("parsed_merchant")
    raw_key = normalize_key(raw_merchant)
    if not raw_key or raw_key == normalize_key(canonical_name):
        return
    get_merchant_alias_collection().update_one(
        {"household_id": household_id, "raw_key": raw_key},
        {
            "$set": {"canonical_name": canonical_name, "raw_variant": raw_merchant, "updated_at": now},
            "$setOnInsert": {"household_id": household_id, "raw_key": raw_key, "created_at": now},
        },
        upsert=True,
    )


def _update_merchant_category_map(
    household_id: ObjectId, merchant_name: str | None, category_id: ObjectId, wallet_id: ObjectId, now: datetime
) -> None:
    merchant_pattern = normalize_merchant(merchant_name)
    if not merchant_pattern:
        return
    # LED-19: aliases lets a *differently-worded* future SMS for the same
    # canonical merchant (e.g. "SWIGGY BANGALORE" vs the "SWIGGY" this entry
    # was keyed on) still fuzzy-match this entry (suggest_category_layered's
    # layer 2) instead of only ever matching the exact wording seen here.
    aliases = [key for key in aliases_for_merchant(merchant_name, household_id) if key != merchant_pattern]
    get_merchant_category_map_collection().update_one(
        {"household_id": household_id, "merchant_pattern": merchant_pattern},
        {
            "$set": {"category_id": category_id, "wallet_id": wallet_id, "aliases": aliases, "updated_at": now},
            "$inc": {"frequency": 1},
            "$setOnInsert": {"household_id": household_id, "merchant_pattern": merchant_pattern, "created_at": now},
        },
        upsert=True,
    )


def _update_merchant_wallet_map(household_id: ObjectId, merchant_name: str | None, wallet_id: ObjectId, now: datetime) -> None:
    """LED-19 learning loop: every accept records merchant -> wallet history
    (mirrors _update_merchant_category_map) so a future SMS from the same
    merchant can be biased toward this wallet once frequency clears
    MERCHANT_WALLET_MAP_MIN_FREQUENCY (see resolve_wallet_layered)."""
    merchant_normalized = normalize_merchant(merchant_name)
    if not merchant_normalized:
        return
    get_merchant_wallet_map_collection().update_one(
        {"household_id": household_id, "merchant_normalized": merchant_normalized},
        {
            "$set": {"wallet_id": wallet_id, "updated_at": now},
            "$inc": {"frequency": 1},
            "$setOnInsert": {"household_id": household_id, "merchant_normalized": merchant_normalized, "created_at": now},
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
    merchant_name = _resolve_merchant_name(inp, sms)

    doc = {
        "household_id": household_id,
        "wallet_id": wallet["_id"],
        "category_id": category["_id"],
        "user_id": ObjectId(user_id),
        "type": txn_type,
        "amount": amount,
        "transfer_to_wallet_id": None,
        "merchant_name": merchant_name,
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

    if inp.merchant_name and inp.merchant_name.strip():
        _write_merchant_alias(household_id, sms, merchant_name, now)
    _update_merchant_category_map(household_id, merchant_name, category["_id"], wallet["_id"], now)
    _update_merchant_wallet_map(household_id, merchant_name, wallet["_id"], now)

    get_sms_inbox_collection().update_one(
        {"_id": sms["_id"]},
        {"$set": {"status": "accepted", "resolved_transaction_id": txn["_id"], "updated_at": now}},
    )

    return txn

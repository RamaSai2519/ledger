from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_sms_inbox_collection, get_transactions_collection, get_wallets_collection
from shared.notify import notify_household
from shared.scope import require_household_id
from shared.sms.types import NON_COMPLETING_TYPES
from shared.sms_parsing import find_dedup_transaction, parse_sms, resolve_wallet, suggest_category, utcnow


def _parse_received_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _base_doc(inp, household_id: ObjectId, user_id: str, now: datetime, received_at: datetime) -> dict:
    return {
        "household_id": household_id,
        "user_id": ObjectId(user_id),
        "raw_text": inp.raw_text,
        "sender_id": inp.sender_id,
        "received_at": received_at,
        "parse_status": "pending",
        "parsed_amount": None,
        "parsed_direction": None,
        "parsed_last4": None,
        "parsed_merchant": None,
        "parsed_ref": None,
        "transaction_type": None,
        "transaction_status": None,
        "merchant_normalized": None,
        "counterparty": None,
        "payment_method": None,
        "balance_after": None,
        "field_confidences": None,
        "parse_evidence": None,
        "suggested_wallet_id": None,
        "suggested_category_id": None,
        "confidence_score": 0.0,
        "status": "suggested",
        "resolved_transaction_id": None,
        "created_at": now,
        "updated_at": now,
    }


def ingest_sms(inp, user_id: str) -> dict:
    # household_id is derived from the authenticated JWT subject's own user
    # doc, never trusted from the request body — this is what keeps
    # /sms/ingest from ever writing/reading across households even though
    # the client-side allow-list filtering (plan.md §2.3) is the SMS
    # pipeline's *other* data-minimization guard.
    household_id = require_household_id(user_id)
    now = utcnow()
    received_at = _parse_received_at(inp.received_at) or now

    doc = _base_doc(inp, household_id, user_id, now, received_at)
    inbox = get_sms_inbox_collection()

    parsed = parse_sms(household_id, inp.sender_id, inp.raw_text, received_at)
    if parsed is None:
        # Classified as a transaction attempt (has a debit/credit-shaped
        # verb) but no amount could be extracted at all — a genuine parse
        # failure, distinct from `not_transaction` below (spec Part 3).
        doc["parse_status"] = "failed"
        result = inbox.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    if not parsed["is_transaction"]:
        # Recognized as OTP/promotional/balance-only/statement/due-reminder/
        # other — correctly *not* a transaction, so no suggestion, no push
        # (spec Part 3). Recorded for audit/debugging only.
        doc["parse_status"] = "not_transaction"
        doc["transaction_type"] = parsed["transaction_type"]
        doc["confidence_score"] = parsed["confidence_score"]
        doc["field_confidences"] = parsed["field_confidences"]
        doc["parse_evidence"] = parsed["parse_evidence"]
        doc["status"] = "not_applicable"
        result = inbox.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    doc["parse_status"] = "parsed"
    doc["parsed_amount"] = parsed["parsed_amount"]
    doc["parsed_direction"] = parsed["parsed_direction"]
    doc["parsed_last4"] = parsed["parsed_last4"]
    doc["parsed_merchant"] = parsed["parsed_merchant"]
    doc["parsed_ref"] = parsed["parsed_ref"]
    doc["transaction_type"] = parsed["transaction_type"]
    doc["transaction_status"] = parsed["transaction_status"]
    doc["merchant_normalized"] = parsed["merchant_normalized"]
    doc["counterparty"] = parsed["counterparty"]
    doc["payment_method"] = parsed["payment_method"]
    doc["balance_after"] = parsed["balance_after"]
    doc["field_confidences"] = parsed["field_confidences"]
    doc["parse_evidence"] = parsed["parse_evidence"]

    # A transaction SMS whose *state* isn't a completed success (a reversed/
    # failed/pending payment) must never silently turn into a suggested
    # expense/income — sms_inbox doesn't yet model those states separately
    # (spec Part 3), so the conservative move is: record it, but never
    # surface it as an actionable suggestion or push.
    if parsed["transaction_type"] in {t.value for t in NON_COMPLETING_TYPES}:
        doc["status"] = "not_applicable"
        result = inbox.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    wallet = resolve_wallet(household_id, parsed["parsed_last4"])
    category_id, mapped_wallet_id, category_confidence = suggest_category(household_id, parsed["parsed_merchant"])

    # If last4 didn't resolve a wallet directly, fall back to whichever
    # wallet this merchant has historically been logged against (learning
    # layer helping wallet resolution too, not just category).
    if wallet is None and mapped_wallet_id is not None:
        wallet = get_wallets_collection().find_one(
            {"_id": mapped_wallet_id, "household_id": household_id, "is_archived": {"$ne": True}}
        )

    doc["suggested_wallet_id"] = wallet["_id"] if wallet else None
    doc["suggested_category_id"] = category_id
    base_confidence = parsed["confidence_score"]
    doc["confidence_score"] = round(
        (base_confidence * 0.6 + category_confidence * 0.4) if wallet else (base_confidence * 0.5), 2
    )

    if wallet is not None:
        existing = find_dedup_transaction(
            household_id, wallet["_id"], parsed["parsed_amount"], received_at, parsed.get("transaction_id")
        )
        if existing is not None:
            # Dedup (plan.md §7 step 11, spec Part 14): silently link
            # instead of prompting again — no sms_inbox status=suggested,
            # no push.
            doc["status"] = "accepted"
            doc["resolved_transaction_id"] = existing["_id"]
            result = inbox.insert_one(doc)
            doc["_id"] = result.inserted_id
            get_transactions_collection().update_one({"_id": existing["_id"]}, {"$set": {"sms_id": doc["_id"]}})
            return doc

    result = inbox.insert_one(doc)
    doc["_id"] = result.inserted_id

    merchant_label = doc["parsed_merchant"] or "a transaction"
    amount = parsed["parsed_amount"]
    verb = "Add as income?" if parsed["parsed_direction"] == "credit" else "Add as an expense?"
    body = f"₹{amount:.0f} at {merchant_label}. {verb}"
    notify_household(
        household_id,
        "sms_suggestion",
        {"sms_id": str(doc["_id"]), "amount": amount, "merchant": doc["parsed_merchant"], "direction": parsed["parsed_direction"]},
        "New transaction detected",
        body,
    )

    return doc

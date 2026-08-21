from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_categories_collection, get_sms_inbox_collection, get_transactions_collection
from shared.notify import notify_household
from shared.scope import require_household_id
from shared.sms.types import NON_COMPLETING_TYPES
from shared.sms_parsing import find_dedup_transaction, parse_sms, resolve_wallet_layered, suggest_category_layered, utcnow


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
        "wallet_confidence": 0.0,
        "category_confidence": 0.0,
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

    # LED-19: layered wallet/category prefill — each degrades through
    # several match strategies (last4/merchant-history/institution/
    # single-wallet/default for wallet; exact/alias/keyword for category)
    # rather than the single exact-match-or-null lookups this used to do, so
    # a suggestion still prefills something actionable even when the SMS
    # lacks a clean last4 or the merchant has never been seen before.
    # merchant_category_map still carries a wallet_id from past accepts
    # (kept for the category side's own bookkeeping), but wallet *suggestion*
    # now goes exclusively through resolve_wallet_layered's own
    # decay-guarded merchant_wallet_map layer below — reusing
    # merchant_category_map.wallet_id here too would let a single accept
    # lock in a wallet with no decay guard at all, defeating the point of
    # MERCHANT_WALLET_MAP_MIN_FREQUENCY.
    category_id, _mapped_wallet_id, category_confidence, _category_layer = suggest_category_layered(
        household_id, parsed["parsed_merchant"]
    )
    wallet, wallet_confidence, _wallet_layer = resolve_wallet_layered(household_id, parsed, inp.raw_text)

    doc["suggested_wallet_id"] = wallet["_id"] if wallet else None
    doc["suggested_category_id"] = category_id
    doc["wallet_confidence"] = round(wallet_confidence, 2)
    doc["category_confidence"] = round(category_confidence, 2)
    base_confidence = parsed["confidence_score"]
    doc["confidence_score"] = round(base_confidence * 0.5 + wallet_confidence * 0.25 + category_confidence * 0.25, 2)

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

    # LED-21: the lock-screen notification (design s21) needs the category
    # guess and wallet label up front — it can't defer to an in-app fetch
    # the way the notifications-list row can, since Confirm/Edit/Dismiss are
    # rendered directly on the notification itself.
    category_name = None
    category_icon = None
    if category_id is not None:
        category = get_categories_collection().find_one({"_id": category_id})
        if category:
            category_name = category.get("name")
            category_icon = category.get("icon")
    wallet_label = None
    if wallet is not None:
        wallet_label = wallet["name"]
        if wallet.get("account_last4"):
            wallet_label += f" ••{wallet['account_last4']}"

    notify_household(
        household_id,
        "sms_suggestion",
        {
            "sms_id": str(doc["_id"]),
            "amount": amount,
            "merchant": doc["parsed_merchant"],
            "direction": parsed["parsed_direction"],
            "category_name": category_name,
            "category_icon": category_icon,
            "wallet_label": wallet_label,
            "can_confirm": category_id is not None and wallet is not None,
        },
        "New transaction detected",
        body,
        push_data_only=True,
    )

    return doc

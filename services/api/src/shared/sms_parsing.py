"""Core SMS-to-transaction-suggestion parsing logic (plan.md §7, LED-7).

Kept separate from models/sms_ingest/compute.py so the matching/extraction/
resolution steps are independently unit-testable and reusable (e.g. from a
future re-parse/backfill job) without going through the full HTTP request
path.
"""
import re
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from shared.db import (
    get_merchant_category_map_collection,
    get_sms_parser_rules_collection,
    get_transactions_collection,
    get_wallets_collection,
)

_DEBIT_KEYWORDS = {"debited", "spent", "paid", "debit"}
_CREDIT_KEYWORDS = {"credited", "received"}

# Dedup tolerance: two amounts on the same wallet within this many rupees on
# the same calendar day are treated as "the same transaction, logged twice"
# per plan.md §7 step 11 ("similar amount").
DEDUP_AMOUNT_TOLERANCE = 1.0


def normalize_merchant(merchant: str | None) -> str:
    """Normalizes a raw extracted merchant string into the lookup key used
    by merchant_category_map — lowercased, alphanumeric-only, so trivial
    formatting differences ("SWIGGY*BLR" vs "Swiggy Blr") still collapse to
    the same learned mapping."""
    if not merchant:
        return ""
    return re.sub(r"[^a-z0-9]", "", merchant.lower())


def _normalize_direction(txn_type: str | None, raw_keyword: str | None) -> str:
    if txn_type in ("debit", "credit"):
        return txn_type
    keyword = (raw_keyword or "").lower()
    if keyword in _CREDIT_KEYWORDS:
        return "credit"
    return "debit"  # conservative default: an unrecognized keyword is treated as spend, not income


def find_matching_rules(household_id: ObjectId, sender_id: str) -> list[dict]:
    """Household-specific custom rules take priority over global ones for
    the same sender_id (plan.md §4: household_id nullable, null = default).
    Falls back to the household-agnostic GENERIC low-confidence rule only if
    nothing else matches this sender at all."""
    collection = get_sms_parser_rules_collection()
    household_rules = list(
        collection.find({"household_id": household_id, "sender_ids": sender_id, "is_active": True})
    )
    if household_rules:
        return household_rules

    global_rules = list(collection.find({"household_id": None, "sender_ids": sender_id, "is_active": True}))
    if global_rules:
        return global_rules

    return list(collection.find({"household_id": None, "bank_code": "GENERIC", "is_active": True}))


def parse_sms(household_id: ObjectId, sender_id: str, raw_text: str) -> dict | None:
    """Returns a dict of extracted fields + confidence_score, or None if no
    rule (including the generic fallback) matched at all."""
    for rule in find_matching_rules(household_id, sender_id):
        is_fallback = rule.get("bank_code") == "GENERIC"
        for pattern in rule.get("patterns", []):
            try:
                compiled = re.compile(pattern["regex"], re.IGNORECASE)
            except re.error:
                continue
            match = compiled.search(raw_text or "")
            if not match:
                continue
            groups = match.groupdict()
            amount_str = groups.get("amount")
            if not amount_str:
                continue
            try:
                amount = float(amount_str.replace(",", ""))
            except ValueError:
                continue

            direction = _normalize_direction(pattern.get("txn_type"), groups.get("direction"))
            last4 = groups.get("last4")
            merchant = (groups.get("merchant") or "").strip() or None

            if is_fallback:
                confidence = 0.3
            elif last4 and merchant:
                confidence = 0.9
            else:
                confidence = 0.6

            return {
                "bank_code": rule.get("bank_code"),
                "parsed_amount": amount,
                "parsed_direction": direction,
                "parsed_last4": last4,
                "parsed_merchant": merchant,
                "parsed_ref": groups.get("ref"),
                "confidence_score": confidence,
            }
    return None


def resolve_wallet(household_id: ObjectId, last4: str | None) -> dict | None:
    """Matches on wallet provider+account_last4 (plan.md §7 step 5). Only
    last4 is used for the DB query (provider isn't reliably derivable from
    SMS sender_id alone across all 8 banks) — an ambiguous match (more than
    one wallet sharing the same last4, e.g. two cards from different banks
    that happen to share last-4) is treated as no match, same as no match at
    all, so the user always picks manually rather than risk crediting the
    wrong wallet."""
    if not last4:
        return None
    wallets = list(
        get_wallets_collection().find({"household_id": household_id, "account_last4": last4, "is_archived": {"$ne": True}})
    )
    return wallets[0] if len(wallets) == 1 else None


def suggest_category(household_id: ObjectId, merchant: str | None) -> tuple[ObjectId | None, ObjectId | None, float]:
    """Frequency-based merchant_category_map lookup (plan.md §7 step 6, the
    "learning" mechanism — no ML). Returns (category_id, wallet_id,
    confidence); wallet_id is only set if this merchant reliably maps to one
    wallet historically."""
    normalized = normalize_merchant(merchant)
    if not normalized:
        return None, None, 0.0
    entry = get_merchant_category_map_collection().find_one({"household_id": household_id, "merchant_pattern": normalized})
    if not entry:
        return None, None, 0.0
    frequency = entry.get("frequency", 1)
    confidence = min(0.95, 0.5 + 0.05 * frequency)
    return entry.get("category_id"), entry.get("wallet_id"), confidence


def find_dedup_transaction(household_id: ObjectId, wallet_id: ObjectId, amount: float, when: datetime) -> dict | None:
    """Same-wallet, similar-amount, same-calendar-day existing transaction
    (plan.md §7 step 11) — if found, the SMS should silently link instead of
    prompting again."""
    day_start = when.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    return get_transactions_collection().find_one(
        {
            "household_id": household_id,
            "wallet_id": wallet_id,
            "type": {"$in": ["expense", "income"]},
            "date": {"$gte": day_start, "$lt": day_end},
            "amount": {"$gte": amount - DEDUP_AMOUNT_TOLERANCE, "$lte": amount + DEDUP_AMOUNT_TOLERANCE},
        }
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

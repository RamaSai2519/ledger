"""Core SMS-to-transaction-suggestion parsing logic (plan.md §7, LED-7,
LED-18).

`parse_sms()` now delegates to the layered pipeline in `shared/sms/` (LED-18)
but keeps returning the same dict shape `models/sms_ingest/compute.py`
already consumes, with new keys added rather than old ones removed/renamed,
so that caller needed no changes beyond reading the new keys it wants.
"""
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from shared.db import (
    get_merchant_alias_collection,
    get_merchant_category_map_collection,
    get_sms_parser_rules_collection,
    get_transactions_collection,
    get_wallets_collection,
)
from shared.sms.deduplicator import TransactionDeduplicator
from shared.sms.merchant_normalizer import normalize_key
from shared.sms.pipeline import SmsParserPipeline
from shared.sms.types import ParsedTransaction

# Dedup tolerance: two amounts on the same wallet within this many rupees on
# the same calendar day are treated as "the same transaction, logged twice"
# per plan.md §7 step 11 ("similar amount"). Still used as the fallback path
# when no transaction ID is available for a fingerprint match.
DEDUP_AMOUNT_TOLERANCE = 1.0

_pipeline = SmsParserPipeline()
_deduplicator = TransactionDeduplicator()


def normalize_merchant(merchant: str | None) -> str:
    """Kept for backwards compatibility with merchant_category_map lookups
    that were built against this exact key format before LED-18 - now a
    thin re-export of shared.sms.merchant_normalizer.normalize_key."""
    return normalize_key(merchant)


def _load_rules(household_id: ObjectId) -> list[dict]:
    """Household-specific custom rules plus every global (household_id=None)
    rule — the full candidate set InstitutionResolver needs, not just rules
    whose sender_ids happen to already match, since body-text evidence
    (bank name mentioned, keywords) can identify the institution even when
    the sender ID itself doesn't match any known variant."""
    collection = get_sms_parser_rules_collection()
    household_rules = list(collection.find({"household_id": household_id, "is_active": True}))
    global_rules = list(collection.find({"household_id": None, "is_active": True}))
    return household_rules + global_rules


def _load_merchant_alias_map() -> dict[str, str]:
    return {doc["raw_key"]: doc["canonical_name"] for doc in get_merchant_alias_collection().find({})}


def parse_sms(household_id: ObjectId, sender_id: str, raw_text: str, received_at: datetime | None = None) -> dict | None:
    """Returns a dict of extracted fields + confidence_score, or None only
    when the message isn't even worth recording as an sms_inbox row (kept
    for signature compatibility - in practice the new pipeline always
    returns *something*, even if `is_transaction=False`, since telling
    "not a transaction" apart from "failed to parse" is itself useful)."""
    rules = _load_rules(household_id)
    merchant_alias_map = _load_merchant_alias_map()
    known_merchants = set(merchant_alias_map.keys())

    parsed: ParsedTransaction = _pipeline.parse(
        sender_id=sender_id,
        raw_text=raw_text,
        received_at=received_at or utcnow(),
        rules=rules,
        merchant_alias_map=merchant_alias_map,
        known_merchants=known_merchants,
    )

    if not parsed.is_transaction:
        return {
            "is_transaction": False,
            "transaction_type": parsed.transaction_type.value,
            "bank_code": parsed.bank_code,
            "confidence_score": parsed.overall_confidence,
            "field_confidences": parsed.field_confidences,
            "parse_evidence": parsed.evidence,
        }

    if parsed.amount is None:
        # Recognized as transactional wording but no amount could be
        # extracted at all - this is the genuine "failed" case (distinct
        # from `is_transaction=False`, which means "correctly recognized as
        # non-transactional").
        return None

    amount = float(parsed.amount.value)
    direction = "credit" if parsed.transaction_type.value in (
        "credit", "upi_receipt", "cash_deposit", "refund", "interest", "salary"
    ) else "debit"

    return {
        "is_transaction": True,
        "bank_code": parsed.bank_code,
        "transaction_type": parsed.transaction_type.value,
        "transaction_status": parsed.transaction_status.value,
        "parsed_amount": amount,
        "parsed_direction": direction,
        "parsed_last4": parsed.account_last4.value if parsed.account_last4 else None,
        "parsed_merchant": parsed.merchant_raw.value if parsed.merchant_raw else None,
        "merchant_normalized": parsed.merchant_normalized.value if parsed.merchant_normalized else None,
        "counterparty": parsed.counterparty.value if parsed.counterparty else None,
        "payment_method": parsed.payment_method.value if parsed.payment_method else None,
        "parsed_ref": parsed.transaction_id.value if parsed.transaction_id else None,
        "transaction_id": parsed.transaction_id.value if parsed.transaction_id else None,
        "balance_after": parsed.balance_after.value if parsed.balance_after else None,
        "transaction_date": parsed.transaction_date.value if parsed.transaction_date else None,
        "date_inferred": parsed.date_inferred,
        "confidence_score": parsed.overall_confidence,
        "field_confidences": parsed.field_confidences,
        "parse_evidence": parsed.evidence,
        "fingerprint": _deduplicator.fingerprint(parsed, parsed.bank_code),
    }


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


def find_dedup_transaction(
    household_id: ObjectId, wallet_id: ObjectId, amount: float, when: datetime, transaction_id: str | None = None
) -> dict | None:
    """Same-wallet, similar-amount, same-calendar-day existing transaction
    (plan.md §7 step 11) — if found, the SMS should silently link instead of
    prompting again. Prefers matching on `transaction_id` (spec Part 14 —
    the only field actually guaranteed unique per real transaction) when one
    was extracted, falling back to the amount+day heuristic otherwise."""
    if transaction_id:
        existing = get_transactions_collection().find_one(
            {"household_id": household_id, "wallet_id": wallet_id, "sms_transaction_id": transaction_id}
        )
        if existing is not None:
            return existing

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

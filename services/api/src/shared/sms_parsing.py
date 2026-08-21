"""Core SMS-to-transaction-suggestion parsing logic (plan.md §7, LED-7,
LED-18).

`parse_sms()` now delegates to the layered pipeline in `shared/sms/` (LED-18)
but keeps returning the same dict shape `models/sms_ingest/compute.py`
already consumes, with new keys added rather than old ones removed/renamed,
so that caller needed no changes beyond reading the new keys it wants.
"""
import re
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from shared.db import (
    get_categories_collection,
    get_category_keyword_rules_collection,
    get_merchant_alias_collection,
    get_merchant_category_map_collection,
    get_merchant_wallet_map_collection,
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
    direction = parsed.direction()

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


# LED-19: minimum accept-with-edited-wallet frequency before merchant_wallet_map
# is trusted to prefill a wallet — a single accidental accept must not
# permanently lock a merchant to the wrong wallet (spec "decay" requirement).
MERCHANT_WALLET_MAP_MIN_FREQUENCY = 2

_WALLET_CONFIDENCE_LAST4 = 0.95
_WALLET_CONFIDENCE_MERCHANT_MAP = 0.8
_WALLET_CONFIDENCE_INSTITUTION = 0.7
_WALLET_CONFIDENCE_SINGLE_WALLET = 0.5
_WALLET_CONFIDENCE_DEFAULT_WALLET = 0.3

_CATEGORY_CONFIDENCE_ALIAS = 0.75
_CATEGORY_CONFIDENCE_KEYWORD = 0.6

# account_last4 was extracted from wording like "Card ending 5678" rather
# than "A/c XX1234" — a (very rough, text-only) signal for which wallet
# *type* the SMS is about, used only when last4 itself didn't resolve a
# wallet directly (spec "Institution + account-type match").
_CARD_WORDING_RE = re.compile(r"\bcard\b", re.IGNORECASE)


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
    """Frequency-based merchant_category_map exact-pattern lookup (plan.md §7
    step 6, the "learning" mechanism — no ML; LED-19 layer 1). Returns
    (category_id, wallet_id, confidence); wallet_id is only set if this
    merchant reliably maps to one wallet historically."""
    normalized = normalize_merchant(merchant)
    if not normalized:
        return None, None, 0.0
    entry = get_merchant_category_map_collection().find_one({"household_id": household_id, "merchant_pattern": normalized})
    if not entry:
        return None, None, 0.0
    frequency = entry.get("frequency", 1)
    confidence = min(0.95, 0.5 + 0.05 * frequency)
    return entry.get("category_id"), entry.get("wallet_id"), confidence


def _suggest_category_by_alias(household_id: ObjectId, normalized: str) -> tuple[ObjectId | None, ObjectId | None]:
    """LED-19 layer 2: a merchant that doesn't exact-match any
    merchant_category_map.merchant_pattern may still match one of its
    `aliases` (other raw spellings of the same canonical merchant, e.g.
    "swiggybangalore" aliasing an entry keyed "swiggy") — see
    `aliases_for_merchant` / how `aliases` gets populated on accept."""
    if not normalized:
        return None, None
    entry = get_merchant_category_map_collection().find_one({"household_id": household_id, "aliases": normalized})
    if not entry:
        return None, None
    return entry.get("category_id"), entry.get("wallet_id")


def _suggest_category_by_keyword(household_id: ObjectId, merchant_raw: str | None) -> ObjectId | None:
    """LED-19 layer 3: small, data-driven keyword -> category-name heuristic
    (shared/category_keyword_rules_seed.py), for merchants with no learned
    mapping at all yet. Only fires if the household actually has a
    non-archived category by that name/type — otherwise the rule
    contributes nothing rather than erroring (spec: rules are "configurable",
    not guaranteed to apply)."""
    if not merchant_raw:
        return None
    text = merchant_raw.upper()
    collection = get_category_keyword_rules_collection()
    rules = list(collection.find({"household_id": household_id, "is_active": True})) + list(
        collection.find({"household_id": None, "is_active": True})
    )
    for rule in rules:
        if any(keyword and keyword.upper() in text for keyword in rule.get("keywords", [])):
            category = get_categories_collection().find_one(
                {
                    "household_id": household_id,
                    "name": rule.get("category_name"),
                    "type": rule.get("category_type"),
                    "is_archived": {"$ne": True},
                }
            )
            if category:
                return category["_id"]
    return None


def suggest_category_layered(
    household_id: ObjectId, merchant_raw: str | None
) -> tuple[ObjectId | None, ObjectId | None, float, str]:
    """LED-19: degrades through exact -> alias -> keyword layers, returning
    (category_id, wallet_id, confidence, layer_name) — the highest-confidence
    match wins, and `layer_name` lets callers/tests see which one fired."""
    category_id, wallet_id, confidence = suggest_category(household_id, merchant_raw)
    if category_id is not None:
        return category_id, wallet_id, confidence, "exact"

    normalized = normalize_merchant(merchant_raw)
    category_id, wallet_id = _suggest_category_by_alias(household_id, normalized)
    if category_id is not None:
        return category_id, wallet_id, _CATEGORY_CONFIDENCE_ALIAS, "alias"

    category_id = _suggest_category_by_keyword(household_id, merchant_raw)
    if category_id is not None:
        return category_id, None, _CATEGORY_CONFIDENCE_KEYWORD, "keyword"

    return None, None, 0.0, "none"


def aliases_for_merchant(merchant_raw: str | None) -> list[str]:
    """Every other raw_key sharing the same canonical `merchant_aliases` name
    as `merchant_raw` — used to populate merchant_category_map.aliases on
    accept so a *future* SMS with a differently-worded variant of the same
    merchant can still fuzzy-match (layer 2 above)."""
    key = normalize_merchant(merchant_raw)
    if not key:
        return []
    alias_doc = get_merchant_alias_collection().find_one({"raw_key": key})
    if not alias_doc:
        return []
    canonical = alias_doc["canonical_name"]
    return [doc["raw_key"] for doc in get_merchant_alias_collection().find({"canonical_name": canonical})]


def _institution_name_tokens(bank_code: str | None) -> list[str]:
    """The word(s) of the global sms_parser_rules institution_name for this
    bank_code (e.g. "HDFC Bank" -> ["HDFC", "Bank"]) — used to fuzzy-match
    against a wallet's free-text `provider` field, since there's no
    structured bank identifier on wallets themselves."""
    if not bank_code:
        return []
    rule = get_sms_parser_rules_collection().find_one({"bank_code": bank_code, "household_id": None})
    if not rule or not rule.get("institution_name"):
        return [bank_code]
    return rule["institution_name"].split()


def _wallet_type_candidates(looks_like_card: bool) -> list[str]:
    return ["credit_card", "pay_later"] if looks_like_card else ["bank_account", "cash"]


def _suggest_wallet_by_institution(household_id: ObjectId, bank_code: str | None, looks_like_card: bool) -> dict | None:
    """LED-19 layer: bias toward the household's wallet for this SMS's
    institution when last4 didn't resolve one directly — an ambiguous match
    (more than one wallet from the same institution/type) is treated as no
    match, same conservative stance as `resolve_wallet`'s last4 lookup."""
    tokens = [t for t in _institution_name_tokens(bank_code) if len(t) > 2]
    if not tokens:
        return None
    candidates = list(
        get_wallets_collection().find(
            {
                "household_id": household_id,
                "type": {"$in": _wallet_type_candidates(looks_like_card)},
                "is_archived": {"$ne": True},
                "provider": {"$exists": True, "$ne": None},
            }
        )
    )
    matches = [
        w for w in candidates if any(token.lower() in (w.get("provider") or "").lower() for token in tokens)
    ]
    return matches[0] if len(matches) == 1 else None


def _suggest_wallet_by_merchant_map(household_id: ObjectId, merchant_raw: str | None) -> dict | None:
    """LED-19 learning loop: an accept with an edited wallet writes
    merchant_normalized -> wallet_id into merchant_wallet_map (mirrors
    merchant_category_map). Only trusted once frequency exceeds
    MERCHANT_WALLET_MAP_MIN_FREQUENCY so one accidental accept can't
    permanently lock a merchant to the wrong wallet (spec "decay")."""
    normalized = normalize_merchant(merchant_raw)
    if not normalized:
        return None
    entry = get_merchant_wallet_map_collection().find_one({"household_id": household_id, "merchant_normalized": normalized})
    if not entry or entry.get("frequency", 0) <= MERCHANT_WALLET_MAP_MIN_FREQUENCY:
        return None
    return get_wallets_collection().find_one(
        {"_id": entry["wallet_id"], "household_id": household_id, "is_archived": {"$ne": True}}
    )


def _suggest_wallet_single_of_type(household_id: ObjectId, looks_like_card: bool) -> dict | None:
    candidates = list(
        get_wallets_collection().find(
            {"household_id": household_id, "type": {"$in": _wallet_type_candidates(looks_like_card)}, "is_archived": {"$ne": True}}
        )
    )
    return candidates[0] if len(candidates) == 1 else None


def _suggest_default_wallet(household_id: ObjectId) -> dict | None:
    return get_wallets_collection().find_one(
        {"household_id": household_id, "is_default": True, "is_archived": {"$ne": True}}
    )


def resolve_wallet_layered(household_id: ObjectId, parsed: dict, raw_text: str) -> tuple[dict | None, float, str]:
    """LED-19: degrades through last4 -> merchant_wallet_map -> institution ->
    single-wallet-of-type -> default-wallet, returning (wallet, confidence,
    layer_name)."""
    wallet = resolve_wallet(household_id, parsed.get("parsed_last4"))
    if wallet is not None:
        return wallet, _WALLET_CONFIDENCE_LAST4, "last4"

    merchant_raw = parsed.get("parsed_merchant")
    wallet = _suggest_wallet_by_merchant_map(household_id, merchant_raw)
    if wallet is not None:
        return wallet, _WALLET_CONFIDENCE_MERCHANT_MAP, "merchant_wallet_map"

    looks_like_card = bool(_CARD_WORDING_RE.search(raw_text or ""))
    wallet = _suggest_wallet_by_institution(household_id, parsed.get("bank_code"), looks_like_card)
    if wallet is not None:
        return wallet, _WALLET_CONFIDENCE_INSTITUTION, "institution"

    wallet = _suggest_wallet_single_of_type(household_id, looks_like_card)
    if wallet is not None:
        return wallet, _WALLET_CONFIDENCE_SINGLE_WALLET, "single_wallet_of_type"

    wallet = _suggest_default_wallet(household_id)
    if wallet is not None:
        return wallet, _WALLET_CONFIDENCE_DEFAULT_WALLET, "default_wallet"

    return None, 0.0, "none"


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

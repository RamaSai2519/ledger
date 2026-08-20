"""Default (global, household_id=None) `sms_parser_rules` seed data for the
8 target banks (plan.md §7, §12, LED-7): Axis, HDFC, Kotak, SBI, Zet Credit
Card, Amazon Pay Later (Axio), Jupiter Credit Card, Canara — plus one
generic low-confidence fallback pattern for unrecognized senders.

Data-driven per CLAUDE.md's non-negotiable constraint (plan.md §2.2): these
rules live in Mongo, not as hardcoded regex in the ingest code path itself
(shared/sms_parsing.py just reads whatever rows exist here) — a broken
parser is fixed by editing/inserting a row, not shipping a release. This
module is only the *seed* — `POST /sms/parser-rules` lets a household add
further custom rules on top without touching code.

Regex groups are intentionally named (amount/last4/merchant/ref, or
`direction` for the generic fallback) so shared/sms_parsing.py can extract
fields generically regardless of which bank's pattern matched. Patterns were
validated by hand against representative sample SMS text for each bank
during development (see LED-7 test fixtures in tests/test_sms_ingest.py) —
bank SMS wording drifts over time, so treat these as a good-enough starting
point to refine from real messages once live, not a guarantee of covering
every format variant a bank ever sends.
"""
from datetime import datetime, timezone

from shared.db import get_sms_parser_rules_collection

# Shared skeleton reused (with only sender-specific wording differences, if
# any bank ever needs them) across most banks: "Rs./INR <amount> ... debited/
# spent/paid ... A/c|Card ...<last4> ... at/to/on/for/towards <merchant>".
_DEBIT_REGEX = (
    r"(?:Rs\.?|INR)\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*"
    r"(?:has been |is |was )?(?:debited|spent|paid|debit)\b.*?"
    r"(?:A/c|Ac|Card|a/c|card)[^\dXx]{0,10}[Xx*]*(?P<last4>\d{4}).*?"
    r"\b(?:at|to|on|for|towards)\b\s+(?P<merchant>[A-Za-z0-9&.\-_' ]{2,40}?)"
    r"(?:\s+on\s+\d|\.|\s*Ref|\s*Avl|\s*$)"
)
_CREDIT_REGEX = (
    r"(?:Rs\.?|INR)\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*"
    r"(?:has been |is |was )?(?:credited|received)\b.*?"
    r"(?:A/c|Ac|a/c)[^\dXx]{0,10}[Xx*]*(?P<last4>\d{4}).*?"
    r"\b(?:from|by)\b\s+(?P<merchant>[A-Za-z0-9&.\-_' ]{2,40}?)"
    r"(?:\s+on\s+\d|\.|\s*Ref|\s*Avl|\s*$)"
)

# Optional trailing reference-number capture some banks append; kept as a
# separate low-priority pattern per bank rather than folded into the main
# regex above, since making `ref` mandatory there would break the common
# case where a message never includes one.
_REF_REGEX_SUFFIX = r".*?Ref\.?\s?(?:No\.?)?\s*[:\-]?\s*(?P<ref>[A-Za-z0-9]+)"

_BANKS = [
    {
        "bank_code": "AXIS",
        "sender_ids": ["AXISBK", "AD-AXISBK", "VM-AXISBK"],
        "institution_name": "Axis Bank",
        "aliases": ["Axis Bank", "Axis"],
        "keywords": ["axis bank"],
    },
    {
        "bank_code": "HDFC",
        "sender_ids": ["HDFCBK", "AD-HDFCBK", "VM-HDFCBK"],
        "institution_name": "HDFC Bank",
        "aliases": ["HDFC Bank", "HDFC"],
        "keywords": ["hdfc bank"],
    },
    {
        "bank_code": "KOTAK",
        "sender_ids": ["KOTAKB", "AD-KOTAKB", "VM-KOTAKB"],
        "institution_name": "Kotak Bank",
        "aliases": ["Kotak Bank", "Kotak Mahindra Bank", "Kotak"],
        "keywords": ["kotak bank"],
    },
    {
        "bank_code": "SBI",
        "sender_ids": ["SBIINB", "SBIUPI", "AD-SBIINB"],
        "institution_name": "State Bank of India",
        "aliases": ["State Bank of India", "SBI"],
        "keywords": ["state bank"],
    },
    {
        "bank_code": "ZET",
        "sender_ids": ["ZETPAY", "AD-ZETPAY"],
        "institution_name": "Zet Credit Card",
        "aliases": ["Zet Card", "Zet"],
        "keywords": ["zet card"],
    },
    {
        "bank_code": "AXIO",
        "sender_ids": ["AXIOPL", "AD-AXIOPL", "AMZNPL"],
        "institution_name": "Axio (Amazon Pay Later)",
        "aliases": ["Axio", "Amazon Pay Later"],
        "keywords": ["pay later"],
    },
    {
        "bank_code": "JUPITER",
        "sender_ids": ["JUPCC", "AD-JUPCC"],
        "institution_name": "Jupiter Credit Card",
        "aliases": ["Jupiter Card", "Jupiter"],
        "keywords": ["jupiter card"],
    },
    {
        "bank_code": "CANARA",
        "sender_ids": ["CANBNK", "AD-CANBNK"],
        "institution_name": "Canara Bank",
        "aliases": ["Canara Bank", "Canara"],
        "keywords": ["canara bank"],
    },
    {
        # LED-18: added from real-world QA (scripts/sms_dev) - a major
        # sender in a live device pull that the original 8-bank seed list
        # didn't cover at all.
        "bank_code": "ICICI",
        "sender_ids": ["ICICIT", "ICICIB", "AD-ICICIT"],
        "institution_name": "ICICI Bank",
        "aliases": ["ICICI Bank", "ICICI"],
        "keywords": ["icici bank"],
    },
]


def _bank_patterns() -> list[dict]:
    return [
        {
            "txn_type": "debit",
            "regex": _DEBIT_REGEX,
            "field_groups": {"amount": "amount", "last4": "last4", "merchant": "merchant"},
        },
        {
            "txn_type": "credit",
            "regex": _CREDIT_REGEX,
            "field_groups": {"amount": "amount", "last4": "last4", "merchant": "merchant"},
        },
    ]


# Generic fallback for senders not on the allow-list of known banks above —
# only extracts amount + debit/credit direction, never last4/merchant, so it
# always yields a low-confidence suggestion that asks the user to pick the
# wallet/category manually (plan.md §4 sms_parser_rules, §12).
_FALLBACK_REGEX = (
    r"(?:Rs\.?|INR)\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*.*?"
    r"\b(?P<direction>debited|credited|spent|received|paid)\b"
)


def default_sms_parser_rules() -> list[dict]:
    """Returns the seed rule docs (without _id/timestamps) — used both by the
    seed script and directly by tests that need a deterministic rule set
    without depending on script execution order."""
    rules = [
        {
            "bank_code": bank["bank_code"],
            "sender_ids": bank["sender_ids"],
            "institution_name": bank["institution_name"],
            "aliases": bank["aliases"],
            "keywords": bank["keywords"],
            "patterns": _bank_patterns(),
            "is_active": True,
            "household_id": None,
        }
        for bank in _BANKS
    ]
    rules.append(
        {
            "bank_code": "GENERIC",
            "sender_ids": [],
            "patterns": [{"txn_type": "generic", "regex": _FALLBACK_REGEX, "field_groups": {"amount": "amount", "direction": "direction"}}],
            "is_active": True,
            "household_id": None,
        }
    )
    return rules


def seed_default_sms_parser_rules() -> int:
    """Idempotent upsert of the global (household_id=None) seed rules, keyed
    by bank_code. Safe to call repeatedly (e.g. on every deploy) — returns
    the number of bank rule sets upserted."""
    collection = get_sms_parser_rules_collection()
    now = datetime.now(timezone.utc)
    count = 0
    for rule in default_sms_parser_rules():
        collection.update_one(
            {"bank_code": rule["bank_code"], "household_id": None},
            {"$set": {**rule, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        count += 1
    return count

"""MerchantExtractor + CounterpartyExtractor + PaymentMethodDetector — spec
Part 6.

Merchant/counterparty are deliberately kept distinct rather than always
filling one "recipient" field: "Paid Rs 500 to Rahul via Google Pay" is a
P2P transfer (counterparty=Rahul, merchant=None), while "Paid Rs 500 to
Swiggy via Google Pay" is a merchant payment (merchant=Swiggy). Since a pure
regex can't reliably tell a person's name from a business name, the
disambiguation prefers a known-merchant lookup (raw text seen before in
`merchant_aliases`, injected by the caller) and otherwise falls back to a
shape heuristic (ALL-CAPS/single-token business-looking strings read as
merchants; Title-Case two-word strings read as person names).
"""
from __future__ import annotations

import re

from shared.sms.merchant_normalizer import normalize_key
from shared.sms.types import FieldValue

_MERCHANT_TOKEN = r"[A-Za-z0-9&.\-_'*/ ]{2,40}?"
# LED-26 real-world finding: bank SMS routinely line-breaks right after the
# merchant/recipient name ("To Netflix\n11/08/26\n..."). _MERCHANT_TOKEN's
# character class can't span that newline, and without re.MULTILINE `$` only
# matches the true end of the whole message - so a name immediately
# followed by "\n" had no valid stop point at all, and the search fell
# through to match a *later* occurrence of the same preposition instead
# (commonly the "Not you? Call X / SMS BLOCK ... to <phone>" fraud-report
# boilerplate, misread as the merchant/counterparty). A bare "\n" stops the
# match right at the line break, same as punctuation already does.
_STOP = r"(?:\s+(?:on|via|using|ref|dt|txn)\b|[.,\n]|\s*$)"

_MERCHANT_CONTEXT_PATTERNS = [
    re.compile(rf"\bPOS\s+(?P<name>{_MERCHANT_TOKEN}){_STOP}", re.IGNORECASE),
    re.compile(rf"\bmerchant\s+(?P<name>{_MERCHANT_TOKEN}){_STOP}", re.IGNORECASE),
    re.compile(rf"\bat\s+(?P<name>{_MERCHANT_TOKEN}){_STOP}", re.IGNORECASE),
    re.compile(rf"\btowards\s+(?P<name>{_MERCHANT_TOKEN}){_STOP}", re.IGNORECASE),
    re.compile(rf"\bfor\s+(?P<name>{_MERCHANT_TOKEN}){_STOP}", re.IGNORECASE),
]

# Ambiguous — could be a merchant ("paid to Swiggy") or a person ("paid to
# Rahul"); resolved by _looks_like_merchant / known-merchant lookup.
_RECIPIENT_PATTERN = re.compile(rf"\bto\s+(?P<name>{_MERCHANT_TOKEN}){_STOP}", re.IGNORECASE)
# Credit-direction equivalent of _RECIPIENT_PATTERN ("credited ... from
# RAMA SATHYA") — same ambiguity, same resolution.
_FROM_PATTERN = re.compile(rf"\bfrom\s+(?P<name>{_MERCHANT_TOKEN}){_STOP}", re.IGNORECASE)
# "to A/c XX9988 from RAMA SATHYA" must not extract "A/c XX9988" as the
# recipient name — it's the household's own account reference, not a
# merchant/counterparty (spec Part 12: merchant must never be an account
# number).
_ACCOUNT_LOOKING = re.compile(r"^(?:A/?c\.?|Acct\.?|Account)\b", re.IGNORECASE)
# Broader than _ACCOUNT_LOOKING: catches an account reference embedded
# *anywhere* in the candidate, not just at the very start - e.g. "sent from
# HDFC Bank A/c XX0000" describes the household's own source account (never
# a counterparty), but only the "A/c XX0000" tail looks account-like.
_CONTAINS_ACCOUNT_REF = re.compile(r"\bA/?c\.?\s*[Xx*]*\d", re.IGNORECASE)
# LED-26 real-world finding: fraud-report boilerplate ("Not you? Call X /
# SMS BLOCK ... to <phone>") and masked-remitter wording ("by an A/C linked
# to mobile x558") both shape-match the "to/from X" recipient patterns just
# as well as a real name does. Neither is a merchant or a person's name —
# they're bare phone numbers or masked references — so both must be
# rejected the same way _ACCOUNT_LOOKING rejects account numbers, rather
# than accepted as the recipient just because they were the first (or only)
# candidate the pattern found.
_MASKED_REF_LOOKING = re.compile(r"^(?:mobile\s+[xX*]*\d+|\d{6,})$")

_VPA_PATTERN = re.compile(r"\bVPA\s+(?P<vpa>[\w.\-]+@[\w.\-]+)", re.IGNORECASE)
# Real-world finding (LED-18): Kotak's UPI-sent template never uses the
# literal word "VPA" at all - "Sent Rs.X ... to <handle>@<bank> on ..." -
# so _VPA_PATTERN alone missed every one of these. The negative lookahead
# excludes an email-shaped domain (has a further ".tld"), same rule the dev
# sanitizer uses to tell a UPI handle apart from an email address.
_BARE_VPA_TO_RE = re.compile(r"\bto\s+(?P<vpa>[\w.\-]+@[a-zA-Z]{2,})\b(?!\.[a-zA-Z])", re.IGNORECASE)
_UPI_P2M_PATTERN = re.compile(r"\bUPI/(?:P2M|DR|CR)/\d+/(?P<name>[A-Za-z0-9&.\-_' ]{2,40})", re.IGNORECASE)
# Real-world finding (LED-26): IMPS credit messages often name the remitter
# between hyphens right after the channel word - "For IMPS
# -INNOFINSOLUTIONSPRIVATELIMITE- <ref>" - with no "on/via/using/ref/dt/txn"
# stop-word and no punctuation before the line break, so the generic
# _MERCHANT_CONTEXT_PATTERNS "for" rule below never finds a place to stop
# matching and silently returns no merchant at all. Anchoring on the second
# hyphen (immediately followed by the numeric reference) gives an explicit,
# reliable stop point for this shape.
_IMPS_DASH_NAME_RE = re.compile(r"\bIMPS\s*-\s*(?P<name>[A-Za-z0-9&.\-_' ]{2,40}?)\s*-\s*\d", re.IGNORECASE)

_PAYMENT_APPS = [
    ("Google Pay", re.compile(r"\b(?:google\s*pay|g-?pay|gpay)\b", re.IGNORECASE)),
    ("PhonePe", re.compile(r"\bphone\s*pe\b", re.IGNORECASE)),
    ("Paytm", re.compile(r"\bpaytm\b", re.IGNORECASE)),
    ("Amazon Pay", re.compile(r"\bamazon\s*pay\b", re.IGNORECASE)),
    ("BHIM", re.compile(r"\bbhim\b", re.IGNORECASE)),
    ("UPI", re.compile(r"\bUPI\b", re.IGNORECASE)),
]

_BUSINESS_SUFFIXES = re.compile(r"\b(?:LTD|LIMITED|PVT|LLP|INC|MART|STORE|STORES|MKTPLACE|RETAIL|FRESH)\b", re.IGNORECASE)


def _clean(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip(" .,-'*")


def _looks_like_merchant(name: str, known_merchants: set[str]) -> bool:
    cleaned = _clean(name)
    if not cleaned:
        return False
    if normalize_key(cleaned) in known_merchants:
        return True
    if _BUSINESS_SUFFIXES.search(cleaned):
        return True
    words = cleaned.split()
    # Single ALL-CAPS token ("AMAZON", "SWIGGY*BLR") reads as a business;
    # two Title-Case words ("Rahul Sharma") reads as a person.
    if len(words) == 1 and cleaned.upper() == cleaned and any(c.isalpha() for c in cleaned):
        return True
    if len(words) >= 2 and all(w[:1].isupper() and w[1:].islower() for w in words if w.isalpha()):
        return False
    return True


class PaymentMethodDetector:
    def detect(self, normalized_text: str) -> FieldValue | None:
        for app_name, pattern in _PAYMENT_APPS:
            if pattern.search(normalized_text):
                return FieldValue(value=app_name, confidence=0.85, evidence=[f"matched \"{app_name}\" keyword"])
        return None


class MerchantExtractor:
    """Returns (merchant, counterparty) — at most one is set, per spec
    Part 6's "never destroy the raw extracted value" + "not every recipient
    is a merchant" requirements."""

    def extract(
        self, normalized_text: str, known_merchants: set[str] | None = None
    ) -> tuple[FieldValue | None, FieldValue | None]:
        known = known_merchants or set()

        vpa_match = _VPA_PATTERN.search(normalized_text)
        if vpa_match:
            vpa = vpa_match.group("vpa")
            handle = vpa.split("@")[0]
            return FieldValue(value=handle, confidence=0.7, evidence=[f"extracted from VPA {vpa}"]), None

        bare_vpa_match = _BARE_VPA_TO_RE.search(normalized_text)
        if bare_vpa_match:
            vpa = bare_vpa_match.group("vpa")
            handle = vpa.split("@")[0]
            if _looks_like_merchant(handle, known):
                return (
                    FieldValue(value=handle, confidence=0.6, evidence=[f"extracted from bare UPI handle {vpa}, resolved as merchant"]),
                    None,
                )
            return (
                None,
                FieldValue(value=handle, confidence=0.55, evidence=[f"extracted from bare UPI handle {vpa}, resolved as counterparty"]),
            )

        p2m_match = _UPI_P2M_PATTERN.search(normalized_text)
        if p2m_match:
            name = _clean(p2m_match.group("name"))
            return FieldValue(value=name, confidence=0.85, evidence=["matched UPI/P2M reference format"]), None

        imps_dash_match = _IMPS_DASH_NAME_RE.search(normalized_text)
        if imps_dash_match:
            name = _clean(imps_dash_match.group("name"))
            if name:
                if _looks_like_merchant(name, known):
                    return (
                        FieldValue(
                            value=name,
                            confidence=0.7,
                            evidence=[f"extracted IMPS dash-delimited name \"{name}\" (business-shaped, resolved as merchant)"],
                        ),
                        None,
                    )
                return (
                    None,
                    FieldValue(
                        value=name,
                        confidence=0.6,
                        evidence=[f"extracted IMPS dash-delimited name \"{name}\" (person-shaped, resolved as counterparty)"],
                    ),
                )

        for pattern in _MERCHANT_CONTEXT_PATTERNS:
            for match in pattern.finditer(normalized_text):
                name = _clean(match.group("name"))
                if not name or _ACCOUNT_LOOKING.match(name) or _CONTAINS_ACCOUNT_REF.search(name) or _MASKED_REF_LOOKING.match(name):
                    continue
                return (
                    FieldValue(value=name, confidence=0.8, evidence=[f"matched merchant-context preposition near \"{name}\""]),
                    None,
                )

        for pattern, preposition in ((_RECIPIENT_PATTERN, "to"), (_FROM_PATTERN, "from")):
            for match in pattern.finditer(normalized_text):
                name = _clean(match.group("name"))
                if not name or _ACCOUNT_LOOKING.match(name) or _CONTAINS_ACCOUNT_REF.search(name) or _MASKED_REF_LOOKING.match(name):
                    continue
                if _looks_like_merchant(name, known):
                    return (
                        FieldValue(value=name, confidence=0.65, evidence=[f"\"{preposition} {name}\" resolved as merchant (known/business-shaped name)"]),
                        None,
                    )
                return (
                    None,
                    FieldValue(value=name, confidence=0.6, evidence=[f"\"{preposition} {name}\" resolved as a person/counterparty, not a merchant"]),
                )

        return None, None

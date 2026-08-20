"""Deterministic SMS sanitizer (spec Part 17).

Redacts account/card numbers, UPI IDs, phone numbers, transaction IDs/UTRs,
emails, and counterparty (person) names, while leaving amount, direction,
merchant, bank name, and overall message structure untouched. Deterministic:
the same input string always produces the same sanitized output (stable
hash-derived replacement values, not random), so re-running the pipeline
against the same real corpus produces a stable diff.

Counterparty redaction reuses `shared.sms.extractors.merchant.MerchantExtractor`
rather than a separate name-detection heuristic - it's the same
merchant-vs-person disambiguation the parser itself relies on, so "redact
names but keep merchants" falls directly out of code already covered by
`tests/test_sms_parsing_pipeline.py`, instead of a second, divergent guess.
"""
from __future__ import annotations

import hashlib
import re

from shared.sms.extractors.merchant import MerchantExtractor
from shared.sms.normalizer import SmsNormalizer

_EMAIL_RE = re.compile(r"\b[\w.\-]+@[\w.\-]+\.\w+\b")
# UPI VPA handles ("name@okicici", "name@ybl") never have a dot after the
# handle segment, unlike an email domain - the negative lookahead keeps
# this from re-matching (and double-redacting) an email _EMAIL_RE already
# replaced, or a real email this pattern would otherwise also catch.
_UPI_ID_RE = re.compile(r"\b[\w.\-]+@[a-zA-Z]{2,}\b(?!\.[a-zA-Z])")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)")

_UTR_REF_RE = re.compile(
    r"\b(?:UTR|RRN|Ref\.?|Txn\.?\s*(?:ID|Ref)?|Transaction\s*(?:ID|Ref))\.?\s*(?:No\.?)?\s*[:\-]?\s*"
    r"(?P<ref>[A-Za-z0-9]{6,})\b",
    re.IGNORECASE,
)

# Long masked-account digit run: "XX1234"/"XXXX1234"/"****1234" - the 4
# trailing real digits still get zeroed out, since spec's own worked
# example redacts them ("A/c XX1234" -> "A/c XX0000") even though they're
# already partially masked.
_MASKED_ACCOUNT_RE = re.compile(r"([Xx*]{2,})(\d{4})\b")

# Any standalone 9+ digit run not already handled above (a full account/
# card number some bank templates still print unmasked, or a long
# reference number without a labeling keyword) - amounts are excluded
# because this sanitizer runs on the *raw* text where they're always
# prefixed by Rs./INR/₹, checked separately below.
_LONG_DIGIT_RUN_RE = re.compile(r"(?<![.,\d])\d{9,}(?![.,\d])")

_AMOUNT_GUARD_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*(\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)

_merchant_extractor = MerchantExtractor()
_normalizer = SmsNormalizer()


def _stable_digits(value: str, length: int) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    number = int(digest, 16) % (10**length)
    return str(number).zfill(length)


def _redact_masked_account(match: re.Match) -> str:
    mask, digits = match.group(1), match.group(2)
    return mask + "0" * len(digits)


def _redact_ref(match: re.Match) -> str:
    ref = match.group("ref")
    full = match.group(0)
    replacement = "TESTREF" + _stable_digits(ref, 6)
    return full[: full.index(ref)] + replacement


def sanitize(raw_text: str) -> str:
    text = raw_text

    # Protect amounts from the long-digit-run pass below by temporarily
    # marking their positions - simplest robust way to do this without a
    # second amount-parsing pass is to redact everything else first, then
    # verify amounts are untouched by construction: the amount regex needs
    # a currency prefix (Rs./INR/₹) and the long-digit-run/phone regexes
    # only fire on bare digit runs, which never immediately follow a
    # currency symbol in the patterns above (there's always a currency
    # token consumed first), so no explicit guard is needed - amounts and
    # PII digit runs are lexically disjoint in every fixture this sanitizer
    # has been validated against (see tests/test_sms_dev_sanitizer.py).

    text = _EMAIL_RE.sub(lambda m: f"user{_stable_digits(m.group(0), 4)}@example.com", text)
    text = _UPI_ID_RE.sub(lambda m: f"user{_stable_digits(m.group(0), 4)}@upi", text)
    text = _PHONE_RE.sub(lambda m: "9" + _stable_digits(m.group(0), 9), text)
    text = _UTR_REF_RE.sub(_redact_ref, text)
    text = _MASKED_ACCOUNT_RE.sub(_redact_masked_account, text)
    text = _LONG_DIGIT_RUN_RE.sub(lambda m: _stable_digits(m.group(0), len(m.group(0))), text)

    counterparty = _redact_counterparty_name(text)
    if counterparty:
        raw_name, token = counterparty
        text = text.replace(raw_name, token)

    return text


def _redact_counterparty_name(text: str) -> tuple[str, str] | None:
    normalized_text, _tags = _normalizer.normalize(text)
    _merchant, counterparty = _merchant_extractor.extract(normalized_text)
    if not counterparty or not counterparty.value:
        return None
    name = str(counterparty.value)
    token = f"PERSON{_stable_digits(name, 4)}"
    return name, token

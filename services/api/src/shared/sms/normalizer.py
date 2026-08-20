"""SmsNormalizer — spec Part 4.

Builds a normalized text view for the rest of the pipeline to pattern-match
against, without ever mutating/discarding the original `raw_text`.
"""
from __future__ import annotations

import re

# Order matters: longer/more-specific spellings first so a shorter one
# doesn't partially consume a longer match.
_CURRENCY_PATTERNS = [
    (re.compile(r"₹\s*"), "RS "),
    (re.compile(r"\bRs\.?\s*", re.IGNORECASE), "RS "),
    (re.compile(r"\bINR\.?\s*", re.IGNORECASE), "RS "),
]

_ACCOUNT_TERMS = re.compile(r"\b(?:A/c|Ac|Acct|Account)\b\.?", re.IGNORECASE)

# Deliberately excludes bare "debit"/"credit" (only the past-tense verb
# forms) - "credit card"/"debit card" are extremely common noun phrases in
# bank SMS that would otherwise false-positive as a transaction verb.
_DEBIT_SYNONYMS = re.compile(r"\b(?:debited|withdrawn|spent|paid|charged|deducted|sent|used)\b", re.IGNORECASE)
_CREDIT_SYNONYMS = re.compile(r"\b(?:credited|received|deposited|added)\b", re.IGNORECASE)
_BALANCE_SYNONYMS = re.compile(
    r"\b(?:Avl\.?\s*Bal|Available\s+Bal(?:ance)?|Current\s+Balance|Bal|Balance)\b", re.IGNORECASE
)


def normalize_currency(text: str) -> str:
    """Collapses every Rs./INR/₹ spelling to a single `RS <amount>` form so
    downstream regexes only need to match one currency token."""
    out = text
    for pattern, replacement in _CURRENCY_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


class SmsNormalizer:
    """Produces `(normalized_text, tags)` — `tags` records which synonym
    classes fired, cheap evidence the classifier/type-detector reuse instead
    of re-scanning the text themselves."""

    def normalize(self, raw_text: str) -> tuple[str, dict[str, bool]]:
        text = raw_text or ""
        text = normalize_currency(text)
        text = _ACCOUNT_TERMS.sub("A/c", text)

        tags = {
            "has_debit_word": bool(_DEBIT_SYNONYMS.search(text)),
            "has_credit_word": bool(_CREDIT_SYNONYMS.search(text)),
            "has_balance_word": bool(_BALANCE_SYNONYMS.search(text)),
        }
        return text, tags

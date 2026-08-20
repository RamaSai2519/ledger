"""TransactionIdExtractor — spec Part 10.

Only matches numbers/alphanumerics explicitly labeled as a reference by the
SMS itself (Ref/UTR/RRN/Txn ID/...) — this keyword-gating is what keeps it
from confusing an OTP, phone number, account number, or bare timestamp for
a transaction ID, since none of those are normally prefixed that way.
"""
from __future__ import annotations

import re

from shared.sms.types import FieldValue

_PATTERNS = [
    (re.compile(r"\bUTR\.?\s*(?:No\.?)?\s*[:\-]?\s*(?P<ref>[A-Za-z0-9]{6,})\b", re.IGNORECASE), "UTR"),
    (re.compile(r"\bRRN\.?\s*[:\-]?\s*(?P<ref>[A-Za-z0-9]{6,})\b", re.IGNORECASE), "RRN"),
    # Real-world finding (LED-18): every component after "UPI"/"Txn" here
    # used to be optional, so "a UPI transaction of Rs.291.17 at Dominos..."
    # matched with the capture landing on the word "transaction" itself -
    # any ordinary sentence containing "UPI transaction <some 6+-letter
    # word>" false-positived as a reference number. The "Ref"/"Txn ID"/
    # "Txn No" label is now mandatory, not optional, so a bare "UPI
    # transaction of" without one of those labels doesn't match at all.
    (re.compile(r"\bUPI\s*(?:Ref\.?|Txn\.?\s*(?:No\.?|ID)?)\s*[:\-]?\s*(?P<ref>[A-Za-z0-9]{6,})\b", re.IGNORECASE), "UPI ref"),
    (re.compile(r"\b(?:Txn|Transaction)\.?\s*(?:ID|Ref)\.?\s*[:\-]?\s*(?P<ref>[A-Za-z0-9]{6,})\b", re.IGNORECASE), "txn ID"),
    # Real-world finding (LED-18, pulled from a live device via
    # scripts/sms_dev): ICICI's credit template is
    # "...Ref<internal-code> no- <REAL_REF> .Thanks" — the internal code
    # glues directly onto "Ref" with *zero* separator and is the same
    # constant string across every message, while the actual unique
    # reference always follows a "no"/colon/dash label. Requiring a
    # mandatory separator after "Ref" (whitespace or `:`/`-`) excludes the
    # glued boilerplate; without this, dozens of unrelated transactions
    # collapsed onto one fingerprint via TransactionDeduplicator, since it
    # prefers the (wrongly) "shared" ref over amount+day matching.
    (re.compile(r"\bRef\.?(?:\s+No\.?)?(?:\s+|[:\-])\s*(?P<ref>[A-Za-z0-9]{6,})\b", re.IGNORECASE), "ref number"),
    (re.compile(r"\bno\.?\s*[:\-]\s*(?P<ref>[A-Za-z0-9]{6,})\b", re.IGNORECASE), "no- ref"),
]

# A bare 6-digit numeric string labeled only "Ref" that's actually plausible
# as an OTP-shaped value gets slightly lower confidence, since some bank
# templates confusingly reuse "Ref" wording near an OTP in the same message
# — evidence trail says why, rather than silently guessing.
_OTP_CONTEXT = re.compile(r"\bOTP\b", re.IGNORECASE)


class TransactionIdExtractor:
    def extract(self, normalized_text: str) -> FieldValue | None:
        for pattern, label in _PATTERNS:
            match = pattern.search(normalized_text)
            if not match:
                continue
            ref = match.group("ref")
            confidence = 0.9
            evidence = [f"matched {label} keyword"]
            if _OTP_CONTEXT.search(normalized_text):
                confidence = 0.6
                evidence.append("message also mentions OTP - lower confidence this is really a transaction ref")
            return FieldValue(value=ref, confidence=confidence, evidence=evidence)
        return None

"""AccountExtractor — spec Part 9.

Normalizes every masked-account spelling down to a bare last-4 digit
string. Never extracts or stores a full account/card number.
"""
from __future__ import annotations

import re

from shared.sms.types import FieldValue

_PATTERNS = [
    re.compile(r"\bcard\s+(?:ending\s+)?(?:in\s+)?[Xx*]*(?P<last4>\d{4})\b", re.IGNORECASE),
    # Mask character count varies by bank - HDFC uses a single "*" (e.g.
    # "A/C *3842") while others use "XX"/"**" (e.g. "A/c XX1234") - both are
    # unambiguous masking, so {1,} rather than {2,}.
    re.compile(r"\b(?:A/c|Ac|Acct|Account)\b\.?[^\dXx*]{0,10}[Xx*]{1,}(?P<last4>\d{4})\b", re.IGNORECASE),
    re.compile(r"\b(?:A/c|Ac|Acct|Account)\b\.?\s*(?P<last4>\d{4})\b", re.IGNORECASE),
    re.compile(r"[Xx*]{1,}(?P<last4>\d{4})\b"),
]


class AccountExtractor:
    def extract(self, normalized_text: str) -> FieldValue | None:
        for pattern in _PATTERNS:
            match = pattern.search(normalized_text)
            if match:
                return FieldValue(
                    value=match.group("last4"), confidence=0.9, evidence=[f"matched masked-account pattern \"{pattern.pattern}\""]
                )
        return None

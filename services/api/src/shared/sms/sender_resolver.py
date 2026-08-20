"""SenderResolver — spec Part 8.

Pure sender-ID matching: normalizes carrier DLT prefixes (AD-, VM-, VK-,
JD-, ...) the same way `SmsAllowlist.kt` does client-side, then checks it
against each institution rule's declared `sender_ids`. Deliberately kept
separate from InstitutionResolver so "sender says X" and "body says X" stay
two independently-weighted pieces of evidence (spec Part 8: "do not trust
sender ID alone").
"""
from __future__ import annotations

import re

_DLT_PREFIX_RE = re.compile(r"^[A-Z]{2}-")
# Real-world finding (LED-18, pulled via scripts/sms_dev from a live
# device): carriers also append a trailing DLT category suffix
# ("VM-HDFCBK-T", "AD-HDFCBK-S") that the seed data's bare "HDFCBK" never
# accounted for - stripping only the leading prefix left ~200 real HDFC
# messages on one device unmatched against an already-seeded bank. `-T`/
# `-S`/etc. is always 1-2 letters, never digits (unlike the 4-digit
# masked-account suffixes this must not accidentally eat).
_DLT_SUFFIX_RE = re.compile(r"-[A-Z]{1,2}$")


def normalize_sender_id(sender_id: str) -> str:
    normalized = (sender_id or "").upper().replace(".", "")
    normalized = _DLT_PREFIX_RE.sub("", normalized)
    return _DLT_SUFFIX_RE.sub("", normalized)


class SenderResolver:
    def matches(self, sender_id: str, candidate_sender_ids: list[str]) -> bool:
        normalized = normalize_sender_id(sender_id)
        return any(normalize_sender_id(candidate) == normalized for candidate in candidate_sender_ids)

"""MerchantNormalizer — spec Part 7.

Maps a raw extracted merchant string ("AMAZON MKTPLACE", "AMZN") to a
canonical display name ("Amazon") via the `merchant_aliases` collection,
which grows from user corrections (see `sms_dev/cli.py review`/`promote-test`
and, in production, whatever correction flow the app's edit-suggestion UI
eventually writes back through). The raw value is always preserved
alongside the normalized one — never destroyed.
"""
from __future__ import annotations

import re

from shared.sms.types import FieldValue


def normalize_key(merchant: str | None) -> str:
    """Same alphanumeric-only lowercasing merchant_category_map lookups use
    (kept identical to the pre-existing shared.sms_parsing.normalize_merchant
    key so learned category mappings don't need re-keying)."""
    if not merchant:
        return ""
    return re.sub(r"[^a-z0-9]", "", merchant.lower())


class MerchantNormalizer:
    def normalize(self, raw_merchant: str, alias_map: dict[str, str] | None = None) -> FieldValue:
        key = normalize_key(raw_merchant)
        alias_map = alias_map or {}
        canonical = alias_map.get(key)
        if canonical:
            return FieldValue(value=canonical, confidence=0.9, evidence=[f"matched merchant_aliases entry for \"{raw_merchant}\""])

        cleaned = re.sub(r"\s+", " ", raw_merchant).strip()
        return FieldValue(value=cleaned, confidence=0.5, evidence=["no known alias, used cleaned raw value"])

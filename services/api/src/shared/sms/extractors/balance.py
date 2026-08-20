"""BalanceExtractor — spec Part 11 (balance/credit-limit family of fields).

Thin, testable wrapper over AmountExtractor's role classification: pulls out
just the non-transaction monetary roles (balance/available balance/credit
limit/minimum due/...) as named fields, so `pipeline.py` doesn't need to
know AmountExtractor's internal role vocabulary.
"""
from __future__ import annotations

from shared.sms.extractors.amount import AmountExtractor
from shared.sms.types import FieldValue

# available_balance and previous_balance both answer "balance after/around
# the transaction" for the purposes of the sms_inbox `balance_after` field;
# credit_limit/available_credit are surfaced separately since they're a
# limit, not a balance.
_BALANCE_AFTER_ROLES = ("available_balance", "previous_balance")


class BalanceExtractor:
    def __init__(self, amount_extractor: AmountExtractor | None = None):
        self._amount_extractor = amount_extractor or AmountExtractor()

    def extract(self, normalized_text: str) -> dict[str, FieldValue]:
        roles = self._amount_extractor.extract(normalized_text)
        result: dict[str, FieldValue] = {}
        for role in _BALANCE_AFTER_ROLES:
            if role in roles:
                result["balance_after"] = roles[role]
                break
        if "credit_limit" in roles:
            result["credit_limit"] = roles["credit_limit"]
        elif "available_credit" in roles:
            result["credit_limit"] = roles["available_credit"]
        if "minimum_due" in roles:
            result["minimum_due"] = roles["minimum_due"]
        return result

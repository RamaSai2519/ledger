"""TransactionValidator — spec Part 12.

Runs after extraction, before confidence scoring, so conflicting evidence
(the merchant field holding the bank's own name, an "amount" that's
actually the balance, an implausible date) demonstrably reduces confidence
rather than being silently accepted.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from shared.sms.types import NON_COMPLETING_TYPES, ParsedTransaction, ValidationIssue

_ALL_DIGITS_RE = re.compile(r"^\d+$")
_FUTURE_TOLERANCE = timedelta(days=1)
_MAX_AGE = timedelta(days=365 * 3)


class TransactionValidator:
    def validate(self, parsed: ParsedTransaction, bank_display_name: str | None, now: datetime | None = None) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        now = now or datetime.now(timezone.utc)

        if parsed.amount is None:
            issues.append(ValidationIssue("amount", "no transaction amount could be extracted", "error"))
        elif parsed.amount.value is None or float(parsed.amount.value) <= 0:
            issues.append(ValidationIssue("amount", "extracted amount is not a positive number", "error"))

        if parsed.transaction_type in NON_COMPLETING_TYPES:
            issues.append(
                ValidationIssue(
                    "transaction_type",
                    f"transaction status is {parsed.transaction_status.value}, not a completed transaction",
                    "warning",
                )
            )

        merchant_value = parsed.merchant_raw.value if parsed.merchant_raw else None
        if merchant_value:
            if bank_display_name and merchant_value.strip().lower() == bank_display_name.strip().lower():
                issues.append(ValidationIssue("merchant", "merchant matches the bank's own name", "warning"))
            if _ALL_DIGITS_RE.match(merchant_value.strip()):
                issues.append(ValidationIssue("merchant", "merchant looks like an account/reference number, not a name", "warning"))

        if parsed.amount and parsed.balance_after and parsed.amount.value == parsed.balance_after.value:
            issues.append(ValidationIssue("amount", "transaction amount equals the balance field - likely misclassified", "warning"))
        if parsed.amount and parsed.credit_limit and parsed.amount.value == parsed.credit_limit.value:
            issues.append(ValidationIssue("amount", "transaction amount equals the credit-limit field - likely misclassified", "warning"))

        if parsed.transaction_id and len(str(parsed.transaction_id.value)) < 4:
            issues.append(ValidationIssue("transaction_id", "extracted transaction ID looks implausibly short", "warning"))

        if parsed.transaction_date:
            date_value = parsed.transaction_date.value
            if isinstance(date_value, datetime):
                compare_now = now if date_value.tzinfo else now.replace(tzinfo=None)
                if date_value > compare_now + _FUTURE_TOLERANCE:
                    issues.append(ValidationIssue("transaction_date", "transaction date is in the future", "warning"))
                elif compare_now - date_value > _MAX_AGE:
                    issues.append(ValidationIssue("transaction_date", "transaction date is implausibly old", "warning"))

        return issues

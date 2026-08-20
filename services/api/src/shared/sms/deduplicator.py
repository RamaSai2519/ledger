"""TransactionDeduplicator — spec Part 14.

The same real-world transaction can arrive as multiple SMS (bank + UPI app,
duplicate carrier delivery, etc.). Builds one fingerprint per parsed
transaction, preferring the bank's own transaction ID when present — the
only field that's actually guaranteed unique per real transaction — and
falling back to a composite of institution/account/amount/type/date/merchant
otherwise.
"""
from __future__ import annotations

from datetime import datetime

from shared.sms.merchant_normalizer import normalize_key
from shared.sms.types import ParsedTransaction


class TransactionDeduplicator:
    def fingerprint(self, parsed: ParsedTransaction, bank_code: str | None) -> str:
        if parsed.transaction_id and parsed.transaction_id.value:
            return f"txnid:{bank_code or 'UNKNOWN'}:{parsed.transaction_id.value}"

        amount = parsed.amount.value if parsed.amount else None
        last4 = parsed.account_last4.value if parsed.account_last4 else None
        merchant = parsed.merchant_raw.value if parsed.merchant_raw else None
        date_value = parsed.transaction_date.value if parsed.transaction_date else None
        day = date_value.strftime("%Y-%m-%d") if isinstance(date_value, datetime) else "unknown"

        return "composite:{bank}:{last4}:{amount}:{type}:{day}:{merchant}".format(
            bank=bank_code or "UNKNOWN",
            last4=last4 or "----",
            amount=amount if amount is not None else "?",
            type=parsed.transaction_type.value,
            day=day,
            merchant=normalize_key(merchant) or "-",
        )

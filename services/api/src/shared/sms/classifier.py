"""TransactionClassifier — spec Part 3.

Coarse first gate: is this SMS even a candidate financial transaction,
before the more expensive extraction layers run. Order matters — OTP and
promotional checks run first since their keywords ("verification code",
"offer") can otherwise coincidentally share words with transaction SMS.
"""
from __future__ import annotations

import re

_OTP_RE = re.compile(r"\b(?:OTP|one[- ]time\s+password|verification\s+code)\b", re.IGNORECASE)
_OTP_CONTEXT_RE = re.compile(r"\bdo\s+not\s+share\b", re.IGNORECASE)

_PROMO_RE = re.compile(
    r"\b(?:offer|sale|discount|cashback\s+offer|% off|flat\s+\d+%|click\s+here|t&c\s+apply|unsubscribe|"
    r"exciting|hurry|limited\s+period)\b",
    re.IGNORECASE,
)

_STATEMENT_RE = re.compile(r"\b(?:e-?statement|statement\s+(?:is\s+)?generated|your\s+statement)\b", re.IGNORECASE)

_DUE_REMINDER_RE = re.compile(
    r"\b(?:payment\s+due|bill\s+due|due\s+on|due\s+date|kindly\s+pay|please\s+pay)\b", re.IGNORECASE
)

# Deliberately excludes bare "debit"/"credit" - "credit card"/"debit card"
# are extremely common noun phrases in bank SMS (including statement/
# due-reminder/promo messages) that would otherwise false-positive as a
# transaction verb.
_TXN_VERB_RE = re.compile(
    r"\b(?:debited|withdrawn|spent|paid|charged|deducted|sent|used|credited|received|deposited|added|"
    r"transferred|refunded|reversed|reversal)\b",
    re.IGNORECASE,
)
# "Your payment ... has failed/is pending" describes a transaction attempt
# by its *outcome* rather than a debit/credit verb - still needs to reach
# the transactional bucket so type_detector can resolve it to
# FAILED_TRANSACTION/PENDING_TRANSACTION, but only when paired with
# payment/transaction wording so a plain "your delivery is pending" doesn't
# false-positive.
_TXN_OUTCOME_RE = re.compile(
    r"\b(?:payment|transaction)\b.{0,60}\b(?:failed|declined|unsuccessful|pending|is\s+being\s+processed)\b",
    re.IGNORECASE,
)

_BALANCE_ONLY_RE = re.compile(
    r"\b(?:avl\.?\s*bal(?:ance)?|available\s+bal(?:ance)?|current\s+bal(?:ance)?|your\s+bal(?:ance)?)\b", re.IGNORECASE
)

Bucket = str  # "otp" | "promotional" | "statement" | "due_reminder" | "balance_only" | "transactional" | "other"


class TransactionClassifier:
    def classify(self, normalized_text: str) -> tuple[Bucket, list[str]]:
        if _OTP_RE.search(normalized_text) or (_OTP_CONTEXT_RE.search(normalized_text) and not _TXN_VERB_RE.search(normalized_text)):
            return "otp", ["matched OTP/verification-code wording"]

        has_txn_verb = bool(_TXN_VERB_RE.search(normalized_text)) or bool(_TXN_OUTCOME_RE.search(normalized_text))

        if _PROMO_RE.search(normalized_text) and not has_txn_verb:
            return "promotional", ["matched promotional keyword, no debit/credit verb present"]

        if has_txn_verb:
            return "transactional", ["matched a debit/credit/transfer verb"]

        if _STATEMENT_RE.search(normalized_text):
            return "statement", ["matched statement-generated wording"]

        if _DUE_REMINDER_RE.search(normalized_text):
            return "due_reminder", ["matched payment-due wording, no debit/credit verb"]

        if _BALANCE_ONLY_RE.search(normalized_text):
            return "balance_only", ["matched balance-inquiry wording, no debit/credit verb"]

        return "other", ["no recognizable financial pattern matched"]

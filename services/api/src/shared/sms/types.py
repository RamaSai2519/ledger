"""Shared enums/dataclasses for the layered SMS parser (LED-18, plan.md §7).

Kept dependency-free (no Mongo/Flask imports) so every other module in this
package, and the pipeline's unit tests, can import from here without pulling
in the rest of the app.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    UPI_PAYMENT = "upi_payment"
    UPI_RECEIPT = "upi_receipt"
    CARD_PAYMENT = "card_payment"
    BANK_TRANSFER = "bank_transfer"
    IMPS = "imps"
    NEFT = "neft"
    RTGS = "rtgs"
    ATM_WITHDRAWAL = "atm_withdrawal"
    CASH_DEPOSIT = "cash_deposit"
    REFUND = "refund"
    REVERSAL = "reversal"
    FAILED_TRANSACTION = "failed_transaction"
    PENDING_TRANSACTION = "pending_transaction"
    AUTOPAY = "autopay"
    EMI_PAYMENT = "emi_payment"
    FEE = "fee"
    INTEREST = "interest"
    SALARY = "salary"
    BALANCE_ONLY = "balance_only"
    OTP = "otp"
    PROMOTIONAL = "promotional"
    STATEMENT = "statement"
    DUE_REMINDER = "due_reminder"
    OTHER = "other"


class TransactionStatus(str, Enum):
    SUCCESS = "success"
    PENDING = "pending"
    FAILED = "failed"
    REVERSED = "reversed"
    REFUNDED = "refunded"


# Types that represent a completed, ledger-worthy movement of money — every
# other type either isn't a transaction at all (OTP/PROMOTIONAL/...) or is a
# transaction whose *state* isn't complete/successful yet, so the pipeline
# must never mint a "suggested" completed-expense/-income for it on its own
# (spec Part 3: "unless the application explicitly represents those states
# separately" — sms_inbox doesn't yet, so we're conservative here).
TRANSACTIONAL_TYPES = {
    TransactionType.DEBIT,
    TransactionType.CREDIT,
    TransactionType.UPI_PAYMENT,
    TransactionType.UPI_RECEIPT,
    TransactionType.CARD_PAYMENT,
    TransactionType.BANK_TRANSFER,
    TransactionType.IMPS,
    TransactionType.NEFT,
    TransactionType.RTGS,
    TransactionType.ATM_WITHDRAWAL,
    TransactionType.CASH_DEPOSIT,
    TransactionType.REFUND,
    TransactionType.AUTOPAY,
    TransactionType.EMI_PAYMENT,
    TransactionType.FEE,
    TransactionType.INTEREST,
    TransactionType.SALARY,
}

# Types that are recognizably financial but must never silently become a
# completed expense/income entry.
NON_COMPLETING_TYPES = {
    TransactionType.REVERSAL,
    TransactionType.FAILED_TRANSACTION,
    TransactionType.PENDING_TRANSACTION,
}

# Types that aren't a transaction at all.
NON_TRANSACTION_TYPES = {
    TransactionType.BALANCE_ONLY,
    TransactionType.OTP,
    TransactionType.PROMOTIONAL,
    TransactionType.STATEMENT,
    TransactionType.DUE_REMINDER,
    TransactionType.OTHER,
}

# Direction each transactional type implies for wallet balance math — used
# to normalize into the existing debit/credit vocabulary the rest of the
# app (wallet balance engine, category suggestion) already speaks.
DEBIT_TYPES = {
    TransactionType.DEBIT,
    TransactionType.UPI_PAYMENT,
    TransactionType.CARD_PAYMENT,
    TransactionType.ATM_WITHDRAWAL,
    TransactionType.AUTOPAY,
    TransactionType.EMI_PAYMENT,
    TransactionType.FEE,
}
CREDIT_TYPES = {
    TransactionType.CREDIT,
    TransactionType.UPI_RECEIPT,
    TransactionType.CASH_DEPOSIT,
    TransactionType.REFUND,
    TransactionType.INTEREST,
    TransactionType.SALARY,
}

# Bank-transfer *channels* rather than directions - a message can say either
# "debited ... towards IMPS" or "Received ... For IMPS", so unlike every
# other type above, membership in TRANSACTIONAL_TYPES alone can't tell us
# which way the money moved. direction() falls back to the credit-verb
# wording itself for these.
_DIRECTION_AMBIGUOUS_TYPES = {
    TransactionType.IMPS,
    TransactionType.NEFT,
    TransactionType.RTGS,
    TransactionType.BANK_TRANSFER,
}
_CREDIT_VERB_RE = re.compile(r"\b(?:credited|received|deposited|added)\b", re.IGNORECASE)


@dataclass
class FieldValue:
    """One extracted field plus why the extractor believes it and how
    confident it is — the spec's "explainable" requirement (Part 13):
    confidence is never a bare number divorced from its reasoning."""

    value: object
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"value": self.value, "confidence": round(self.confidence, 2), "evidence": list(self.evidence)}


@dataclass
class AmountCandidate:
    """One monetary value found anywhere in the SMS, before it's been
    classified as the transaction amount vs balance vs credit limit etc.
    (Part 5 — "NEVER simply take the first numeric value")."""

    raw: str
    value: float
    start: int
    end: int
    role: str | None = None  # "transaction" | "balance" | "available_balance" | "credit_limit" |
    # "available_credit" | "minimum_due" | "total_due" | "emi" | "fee" | "cashback" | "refund" | "previous_balance"
    role_confidence: float = 0.0
    role_evidence: list[str] = field(default_factory=list)


@dataclass
class ValidationIssue:
    field: str
    message: str
    severity: str = "error"  # "error" downgrades to not-a-transaction/failed, "warning" only dents confidence


@dataclass
class ParsedTransaction:
    """The pipeline's final output — one of every field the spec asks for,
    each either a `FieldValue` or `None` when evidence was insufficient
    (Part 13: "if a field cannot be confidently established, return null
    instead of guessing")."""

    raw_text: str
    normalized_text: str
    sender_id: str
    bank_code: str | None
    institution_confidence: float
    transaction_type: TransactionType
    transaction_status: TransactionStatus
    is_transaction: bool

    amount: FieldValue | None = None
    balance_after: FieldValue | None = None
    available_balance: FieldValue | None = None
    credit_limit: FieldValue | None = None
    minimum_due: FieldValue | None = None

    merchant_raw: FieldValue | None = None
    merchant_normalized: FieldValue | None = None
    counterparty: FieldValue | None = None
    payment_method: FieldValue | None = None

    account_last4: FieldValue | None = None
    transaction_id: FieldValue | None = None
    transaction_date: FieldValue | None = None
    date_inferred: bool = False

    validation_issues: list[ValidationIssue] = field(default_factory=list)
    overall_confidence: float = 0.0
    field_confidences: dict = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)

    def direction(self) -> str:
        if self.transaction_type in CREDIT_TYPES:
            return "credit"
        if self.transaction_type in _DIRECTION_AMBIGUOUS_TYPES and _CREDIT_VERB_RE.search(self.normalized_text):
            return "credit"
        return "debit"

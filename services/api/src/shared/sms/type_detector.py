"""TransactionTypeDetector — spec Part 3.

Given the classifier's coarse "transactional" bucket, resolves the precise
`TransactionType` + `TransactionStatus`. Checked most-specific-first so a
message that's both "UPI" and "failed" resolves to FAILED_TRANSACTION
rather than UPI_PAYMENT — status always trumps channel when the transaction
didn't actually complete.
"""
from __future__ import annotations

import re

from shared.sms.types import CREDIT_TYPES, TransactionStatus, TransactionType

_REVERSED_RE = re.compile(r"\b(?:reversed|reversal)\b", re.IGNORECASE)
# Real-world finding (LED-18, human-reviewed via scripts/sms_dev): "Your
# payment ... was not completed. Any amount if debited will be refunded"
# doesn't contain the literal word "failed", so it fell through to the
# REFUND check below and got labeled as a completed refund rather than the
# failed-then-conditionally-refunded attempt it actually describes.
_FAILED_RE = re.compile(r"\b(?:failed|declined|unsuccessful|not\s+processed|not\s+completed)\b", re.IGNORECASE)
_PENDING_RE = re.compile(r"\b(?:pending|processing|is\s+being\s+processed)\b", re.IGNORECASE)
_REFUND_RE = re.compile(r"\brefund(?:ed)?\b", re.IGNORECASE)
_ATM_RE = re.compile(r"\bATM\b", re.IGNORECASE)
_CASH_DEPOSIT_RE = re.compile(r"\bcash\s+deposit(?:ed)?\b", re.IGNORECASE)
_EMI_RE = re.compile(r"\bEMI\b", re.IGNORECASE)
_SALARY_RE = re.compile(r"\bsalary\b", re.IGNORECASE)
_AUTOPAY_RE = re.compile(r"\b(?:autopay|auto[- ]debit|standing\s+instruction)\b", re.IGNORECASE)
_FEE_RE = re.compile(r"\b(?:fee|charges?)\s+(?:of\s+)?(?:debited|charged|levied)\b", re.IGNORECASE)
_INTEREST_RE = re.compile(r"\binterest\s+credited\b", re.IGNORECASE)
_IMPS_RE = re.compile(r"\bIMPS\b", re.IGNORECASE)
_NEFT_RE = re.compile(r"\bNEFT\b", re.IGNORECASE)
_RTGS_RE = re.compile(r"\bRTGS\b", re.IGNORECASE)
# A named UPI app (PhonePe/GPay/Paytm/BHIM) implies the UPI channel just as
# much as the literal word "UPI" does - a message can say "via PhonePe"
# without ever spelling out "UPI". "Amazon Pay" is deliberately excluded:
# "Amazon Pay Later" (a pay-later credit product, seeded as bank_code AXIO)
# would otherwise falsely classify as UPI on the word "Pay" alone.
_UPI_RE = re.compile(r"\b(?:UPI|google\s*pay|g-?pay|gpay|phone\s*pe|paytm|bhim)\b", re.IGNORECASE)
_CARD_RE = re.compile(r"\bcard\b", re.IGNORECASE)
_TRANSFER_RE = re.compile(r"\btransferred\b", re.IGNORECASE)
_CREDIT_VERB_RE = re.compile(r"\b(?:credited|received|deposited|added)\b", re.IGNORECASE)


class TransactionTypeDetector:
    def detect(self, normalized_text: str) -> tuple[TransactionType, TransactionStatus, list[str]]:
        if _REVERSED_RE.search(normalized_text):
            return TransactionType.REVERSAL, TransactionStatus.REVERSED, ["matched reversal wording"]
        if _FAILED_RE.search(normalized_text):
            return TransactionType.FAILED_TRANSACTION, TransactionStatus.FAILED, ["matched failed/declined wording"]
        if _PENDING_RE.search(normalized_text):
            return TransactionType.PENDING_TRANSACTION, TransactionStatus.PENDING, ["matched pending/processing wording"]
        if _REFUND_RE.search(normalized_text):
            return TransactionType.REFUND, TransactionStatus.REFUNDED, ["matched refund wording"]
        if _ATM_RE.search(normalized_text):
            return TransactionType.ATM_WITHDRAWAL, TransactionStatus.SUCCESS, ["matched ATM wording"]
        if _CASH_DEPOSIT_RE.search(normalized_text):
            return TransactionType.CASH_DEPOSIT, TransactionStatus.SUCCESS, ["matched cash-deposit wording"]
        if _EMI_RE.search(normalized_text):
            return TransactionType.EMI_PAYMENT, TransactionStatus.SUCCESS, ["matched EMI wording"]
        if _SALARY_RE.search(normalized_text):
            return TransactionType.SALARY, TransactionStatus.SUCCESS, ["matched salary wording"]
        if _AUTOPAY_RE.search(normalized_text):
            return TransactionType.AUTOPAY, TransactionStatus.SUCCESS, ["matched autopay/standing-instruction wording"]
        if _FEE_RE.search(normalized_text):
            return TransactionType.FEE, TransactionStatus.SUCCESS, ["matched fee/charges wording"]
        if _INTEREST_RE.search(normalized_text):
            return TransactionType.INTEREST, TransactionStatus.SUCCESS, ["matched interest-credited wording"]
        if _IMPS_RE.search(normalized_text):
            return TransactionType.IMPS, TransactionStatus.SUCCESS, ["matched IMPS wording"]
        if _NEFT_RE.search(normalized_text):
            return TransactionType.NEFT, TransactionStatus.SUCCESS, ["matched NEFT wording"]
        if _RTGS_RE.search(normalized_text):
            return TransactionType.RTGS, TransactionStatus.SUCCESS, ["matched RTGS wording"]
        if _UPI_RE.search(normalized_text):
            if _CREDIT_VERB_RE.search(normalized_text):
                return TransactionType.UPI_RECEIPT, TransactionStatus.SUCCESS, ["matched UPI + credit wording"]
            return TransactionType.UPI_PAYMENT, TransactionStatus.SUCCESS, ["matched UPI + debit wording"]
        if _CARD_RE.search(normalized_text) and not _CREDIT_VERB_RE.search(normalized_text):
            return TransactionType.CARD_PAYMENT, TransactionStatus.SUCCESS, ["matched card + debit wording"]
        if _TRANSFER_RE.search(normalized_text):
            return TransactionType.BANK_TRANSFER, TransactionStatus.SUCCESS, ["matched generic transfer wording"]

        if _CREDIT_VERB_RE.search(normalized_text):
            return TransactionType.CREDIT, TransactionStatus.SUCCESS, ["generic credit verb, no more specific channel matched"]
        return TransactionType.DEBIT, TransactionStatus.SUCCESS, ["generic debit verb, no more specific channel matched"]

    def detect_non_transactional(self, bucket: str) -> TransactionType:
        return {
            "otp": TransactionType.OTP,
            "promotional": TransactionType.PROMOTIONAL,
            "statement": TransactionType.STATEMENT,
            "due_reminder": TransactionType.DUE_REMINDER,
            "balance_only": TransactionType.BALANCE_ONLY,
        }.get(bucket, TransactionType.OTHER)


def type_implies_credit(transaction_type: TransactionType) -> bool:
    return transaction_type in CREDIT_TYPES

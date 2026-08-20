"""Pipeline orchestrator — spec's full layered flow:

SMS -> Normalization -> Classification -> Sender/Institution resolution ->
Type detection -> Candidate extraction -> Merchant/counterparty extraction
-> Bank resolution -> Validation -> Confidence scoring -> (Dedup happens one
layer up, in shared/sms_parsing.py, since it needs DB access to existing
transactions) -> Normalized transaction.

Every extractor/resolver/scorer in this package is a small, independently
unit-testable pure function/class; this module just wires them together in
the documented order and is itself the thing `shared/sms_parsing.py` calls.
"""
from __future__ import annotations

from datetime import datetime

from shared.sms.classifier import TransactionClassifier
from shared.sms.confidence import ConfidenceScorer
from shared.sms.extractors.account import AccountExtractor
from shared.sms.extractors.amount import AmountExtractor
from shared.sms.extractors.balance import BalanceExtractor
from shared.sms.extractors.date import DateExtractor
from shared.sms.extractors.merchant import MerchantExtractor, PaymentMethodDetector
from shared.sms.extractors.transaction_id import TransactionIdExtractor
from shared.sms.fallback import TransactionParserFallback
from shared.sms.institution_resolver import InstitutionResolver
from shared.sms.merchant_normalizer import MerchantNormalizer
from shared.sms.normalizer import SmsNormalizer
from shared.sms.type_detector import TransactionTypeDetector
from shared.sms.types import ParsedTransaction, TransactionStatus, TransactionType
from shared.sms.validator import TransactionValidator

_NON_TRANSACTIONAL_BUCKETS = {"otp", "promotional", "statement", "due_reminder", "balance_only", "other"}

# Low overall confidence is the trigger for trying the (currently
# unimplemented-by-default) ML fallback per spec Part 15.
_FALLBACK_THRESHOLD = 0.4


class SmsParserPipeline:
    def __init__(
        self,
        normalizer: SmsNormalizer | None = None,
        classifier: TransactionClassifier | None = None,
        institution_resolver: InstitutionResolver | None = None,
        type_detector: TransactionTypeDetector | None = None,
        amount_extractor: AmountExtractor | None = None,
        balance_extractor: BalanceExtractor | None = None,
        merchant_extractor: MerchantExtractor | None = None,
        payment_method_detector: PaymentMethodDetector | None = None,
        account_extractor: AccountExtractor | None = None,
        transaction_id_extractor: TransactionIdExtractor | None = None,
        date_extractor: DateExtractor | None = None,
        merchant_normalizer: MerchantNormalizer | None = None,
        validator: TransactionValidator | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
        fallback: TransactionParserFallback | None = None,
    ):
        self.normalizer = normalizer or SmsNormalizer()
        self.classifier = classifier or TransactionClassifier()
        self.institution_resolver = institution_resolver or InstitutionResolver()
        self.type_detector = type_detector or TransactionTypeDetector()
        self.amount_extractor = amount_extractor or AmountExtractor()
        self.balance_extractor = balance_extractor or BalanceExtractor(self.amount_extractor)
        self.merchant_extractor = merchant_extractor or MerchantExtractor()
        self.payment_method_detector = payment_method_detector or PaymentMethodDetector()
        self.account_extractor = account_extractor or AccountExtractor()
        self.transaction_id_extractor = transaction_id_extractor or TransactionIdExtractor()
        self.date_extractor = date_extractor or DateExtractor()
        self.merchant_normalizer = merchant_normalizer or MerchantNormalizer()
        self.validator = validator or TransactionValidator()
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        self.fallback = fallback

    def parse(
        self,
        sender_id: str,
        raw_text: str,
        received_at: datetime,
        rules: list[dict],
        merchant_alias_map: dict[str, str] | None = None,
        known_merchants: set[str] | None = None,
    ) -> ParsedTransaction:
        normalized_text, _tags = self.normalizer.normalize(raw_text)
        bucket, class_evidence = self.classifier.classify(normalized_text)
        bank_code, inst_conf, inst_evidence = self.institution_resolver.resolve(sender_id, normalized_text, rules)

        if bucket in _NON_TRANSACTIONAL_BUCKETS:
            transaction_type = self.type_detector.detect_non_transactional(bucket)
            return ParsedTransaction(
                raw_text=raw_text,
                normalized_text=normalized_text,
                sender_id=sender_id,
                bank_code=bank_code,
                institution_confidence=inst_conf,
                transaction_type=transaction_type,
                transaction_status=TransactionStatus.SUCCESS,
                is_transaction=False,
                overall_confidence=inst_conf,
                field_confidences={"institution": round(inst_conf, 2)},
                evidence=class_evidence + inst_evidence,
            )

        transaction_type, transaction_status, type_evidence = self.type_detector.detect(normalized_text)

        amounts = self.amount_extractor.extract(normalized_text)
        amount_fv = amounts.get("transaction")
        balances = self.balance_extractor.extract(normalized_text)

        merchant_fv, counterparty_fv = self.merchant_extractor.extract(normalized_text, known_merchants)
        payment_method_fv = self.payment_method_detector.detect(normalized_text)
        account_fv = self.account_extractor.extract(normalized_text)
        transaction_id_fv = self.transaction_id_extractor.extract(normalized_text)
        date_fv = self.date_extractor.extract(raw_text, received_at)
        date_inferred = bool(date_fv.evidence) and "inferred" in date_fv.evidence[0]

        merchant_normalized_fv = None
        if merchant_fv and merchant_fv.value:
            merchant_normalized_fv = self.merchant_normalizer.normalize(str(merchant_fv.value), merchant_alias_map)

        parsed = ParsedTransaction(
            raw_text=raw_text,
            normalized_text=normalized_text,
            sender_id=sender_id,
            bank_code=bank_code,
            institution_confidence=inst_conf,
            transaction_type=transaction_type,
            transaction_status=transaction_status,
            is_transaction=True,
            amount=amount_fv,
            balance_after=balances.get("balance_after"),
            credit_limit=balances.get("credit_limit"),
            minimum_due=balances.get("minimum_due"),
            merchant_raw=merchant_fv,
            merchant_normalized=merchant_normalized_fv,
            counterparty=counterparty_fv,
            payment_method=payment_method_fv,
            account_last4=account_fv,
            transaction_id=transaction_id_fv,
            transaction_date=date_fv,
            date_inferred=date_inferred,
            evidence=class_evidence + type_evidence + inst_evidence,
        )

        parsed.validation_issues = self.validator.validate(parsed, bank_display_name=bank_code)
        overall, field_confidences = self.confidence_scorer.score(parsed, inst_conf)
        parsed.overall_confidence = overall
        parsed.field_confidences = field_confidences

        if overall < _FALLBACK_THRESHOLD and self.fallback is not None:
            fallback_result = self._try_fallback(sender_id, raw_text, received_at, bank_code)
            if fallback_result is not None and fallback_result.overall_confidence > overall:
                return fallback_result

        return parsed

    def _try_fallback(
        self, sender_id: str, raw_text: str, received_at: datetime, bank_code: str | None
    ) -> ParsedTransaction | None:
        assert self.fallback is not None
        result = self.fallback.parse(raw_text, sender_id, received_at)
        if result is None:
            return None
        result.validation_issues = self.validator.validate(result, bank_display_name=bank_code)
        overall, field_confidences = self.confidence_scorer.score(result, result.institution_confidence)
        result.overall_confidence = overall
        result.field_confidences = field_confidences
        return result

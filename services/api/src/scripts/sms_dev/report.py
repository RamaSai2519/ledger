"""Shared report-building/rendering for the sms_dev pipeline (spec Parts
18/21). Hard rule enforced throughout this package: nothing here ever
prints or writes `raw_text` - only the sanitized body.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from shared.sms.deduplicator import TransactionDeduplicator
from shared.sms.pipeline import SmsParserPipeline
from shared.sms_parser_rules_seed import default_sms_parser_rules

_RULES = default_sms_parser_rules()
_pipeline = SmsParserPipeline()
_deduplicator = TransactionDeduplicator()

LOW_CONFIDENCE_THRESHOLD = 0.6


@dataclass
class ParseResult:
    message_id: str
    sender_id: str
    sanitized_text: str
    is_transaction: bool
    transaction_type: str
    confidence: float
    amount: float | None
    merchant: str | None
    bank_code: str | None
    fingerprint: str | None = None
    evidence: list[str] = field(default_factory=list)
    error: str | None = None


def parse_sanitized_messages(messages: list[dict]) -> list[ParseResult]:
    """`messages` items: {"id", "sender_id", "sanitized_text"} - the only
    fields anything downstream of the sanitizer is allowed to touch."""
    results = []
    for msg in messages:
        try:
            parsed = _pipeline.parse(
                sender_id=msg["sender_id"],
                raw_text=msg["sanitized_text"],
                received_at=datetime.now(timezone.utc),
                rules=_RULES,
            )
            results.append(
                ParseResult(
                    message_id=msg["id"],
                    sender_id=msg["sender_id"],
                    sanitized_text=msg["sanitized_text"],
                    is_transaction=parsed.is_transaction,
                    transaction_type=parsed.transaction_type.value,
                    confidence=parsed.overall_confidence if parsed.is_transaction else parsed.institution_confidence,
                    amount=float(parsed.amount.value) if parsed.amount else None,
                    merchant=str(parsed.merchant_raw.value) if parsed.merchant_raw else None,
                    bank_code=parsed.bank_code,
                    fingerprint=_deduplicator.fingerprint(parsed, parsed.bank_code) if parsed.is_transaction else None,
                    evidence=parsed.evidence,
                )
            )
        except Exception as e:  # noqa: BLE001 - a parser bug on one message must not abort the whole batch
            results.append(
                ParseResult(
                    message_id=msg["id"],
                    sender_id=msg["sender_id"],
                    sanitized_text=msg["sanitized_text"],
                    is_transaction=False,
                    transaction_type="error",
                    confidence=0.0,
                    amount=None,
                    merchant=None,
                    bank_code=None,
                    error=str(e),
                )
            )
    return results


def summarize(results: list[ParseResult]) -> dict:
    transactional = [r for r in results if r.is_transaction]
    non_transactional = [r for r in results if not r.is_transaction and r.error is None]
    errors = [r for r in results if r.error is not None]
    low_confidence = [r for r in transactional if r.confidence < LOW_CONFIDENCE_THRESHOLD]
    high_confidence = [r for r in transactional if r.confidence >= LOW_CONFIDENCE_THRESHOLD]

    return {
        "total": len(results),
        "transactional": len(transactional),
        "non_transactional": len(non_transactional),
        "parser_errors": len(errors),
        "missing_amount": len([r for r in transactional if r.amount is None]),
        "missing_merchant": len([r for r in transactional if r.merchant is None]),
        "missing_bank": len([r for r in transactional if r.bank_code is None]),
        "low_confidence": len(low_confidence),
        "high_confidence": len(high_confidence),
    }


def find_duplicate_candidates(results: list[ParseResult]) -> dict[str, list[str]]:
    fingerprints: dict[str, list[str]] = {}
    for r in results:
        if not r.fingerprint:
            continue
        fingerprints.setdefault(r.fingerprint, []).append(r.message_id)
    return {fp: ids for fp, ids in fingerprints.items() if len(ids) > 1}


def print_report(results: list[ParseResult]) -> None:
    summary = summarize(results)
    print("=== SMS parse report ===")
    for key, value in summary.items():
        print(f"{key:>18}: {value}")

    print("\n=== duplicate fingerprint candidates ===")
    dupes = find_duplicate_candidates(results)
    if not dupes:
        print("(none)")
    for fp, ids in dupes.items():
        print(f"  {fp} -> {ids}")

    print("\n=== per-message detail (sanitized text only) ===")
    for r in results:
        marker = "ERROR" if r.error else ("TXN " if r.is_transaction else "----")
        print(f"[{marker}] id={r.message_id} sender={r.sender_id} type={r.transaction_type} conf={r.confidence:.2f}")
        print(f"         text: {r.sanitized_text}")
        if r.is_transaction:
            print(f"         amount={r.amount} merchant={r.merchant} bank={r.bank_code}")
            print(f"         evidence: {'; '.join(r.evidence)}")
        if r.error:
            print(f"         error: {r.error}")

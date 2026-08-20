"""ConfidenceScorer — spec Part 13.

Turns each field's own confidence + the validator's issue list into one
explainable `overall_confidence`, and a `field_confidences` map the API
response can expose as-is. Validation errors are weighted far more heavily
than warnings, per spec Part 21's "minimize false positives" priority —
better to under-confidence a real transaction into manual review than to
over-confidence a misread one into an auto-suggested expense.
"""
from __future__ import annotations

from shared.sms.types import ParsedTransaction

_ERROR_PENALTY = 0.35
_WARNING_PENALTY = 0.12

_FIELD_WEIGHTS = {
    "amount": 0.4,
    "merchant_raw": 0.2,
    "account_last4": 0.15,
    "transaction_type": 0.15,
    "transaction_date": 0.1,
}


class ConfidenceScorer:
    def score(self, parsed: ParsedTransaction, institution_confidence: float) -> tuple[float, dict[str, float]]:
        field_confidences: dict[str, float] = {"institution": round(institution_confidence, 2)}
        weighted_sum = 0.0
        weight_total = 0.0

        for field_name, weight in _FIELD_WEIGHTS.items():
            if field_name == "transaction_type":
                # Not a FieldValue on ParsedTransaction - anchor it to
                # institution confidence, since type detection quality
                # tracks how confidently we resolved the sender/grammar.
                value = institution_confidence
            else:
                field_value = getattr(parsed, field_name, None)
                if field_value is None:
                    continue
                value = field_value.confidence
            field_confidences[field_name] = round(value, 2)
            weighted_sum += value * weight
            weight_total += weight

        base = (weighted_sum / weight_total) if weight_total else 0.0

        penalty = sum(
            _ERROR_PENALTY if issue.severity == "error" else _WARNING_PENALTY for issue in parsed.validation_issues
        )
        overall = max(0.0, min(1.0, base - penalty))
        return round(overall, 2), field_confidences

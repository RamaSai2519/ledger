import re

from shared.output import ValidationError

ALLOWED_TXN_TYPES = {"debit", "credit"}


def validate(inp) -> None:
    if not inp.bank_code or not inp.bank_code.strip():
        raise ValidationError("bank_code_required")

    if not isinstance(inp.sender_ids, list) or not inp.sender_ids:
        raise ValidationError("sender_ids_must_be_a_non_empty_list")
    for sender_id in inp.sender_ids:
        if not isinstance(sender_id, str) or not sender_id.strip():
            raise ValidationError("sender_ids_must_be_non_empty_strings")

    if not isinstance(inp.patterns, list) or not inp.patterns:
        raise ValidationError("patterns_must_be_a_non_empty_list")

    for pattern in inp.patterns:
        if not isinstance(pattern, dict):
            raise ValidationError("each_pattern_must_be_an_object")
        regex = pattern.get("regex")
        if not regex or not isinstance(regex, str):
            raise ValidationError(f"pattern_regex_required: bank_code={inp.bank_code}")
        try:
            re.compile(regex)
        except re.error as exc:
            raise ValidationError(f"invalid_pattern_regex: bank_code={inp.bank_code} pattern={regex!r} error={exc}") from exc
        txn_type = pattern.get("txn_type")
        if txn_type is not None and txn_type not in ALLOWED_TXN_TYPES:
            raise ValidationError(f"invalid_pattern_txn_type: bank_code={inp.bank_code} txn_type={txn_type}")

    if not isinstance(inp.is_active, bool):
        raise ValidationError("is_active_must_be_a_boolean")

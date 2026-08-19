from shared.balance import CREATABLE_WALLET_TYPES
from shared.output import ValidationError

ALLOWED_TYPE_DETAIL_KEYS = {
    "credit_card": {"credit_limit", "statement_day", "due_day", "min_due_percent"},
    "pay_later": {"credit_limit", "billing_cycle_day", "due_day"},
}


def validate(inp) -> None:
    if not inp.name or not inp.name.strip():
        raise ValidationError("wallet_name_required")
    if inp.type not in CREATABLE_WALLET_TYPES:
        raise ValidationError(f"invalid_wallet_type: {inp.type}")
    if not isinstance(inp.opening_balance, (int, float)):
        raise ValidationError("opening_balance_must_be_numeric")

    detail_field = {
        "credit_card": "credit_card_details",
        "pay_later": "pay_later_details",
    }.get(inp.type)
    if detail_field:
        details = getattr(inp, detail_field)
        if details is not None and not isinstance(details, dict):
            raise ValidationError(f"{detail_field}_must_be_object")

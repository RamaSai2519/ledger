from datetime import datetime

from shared.output import ValidationError
from shared.recurring import RECURRING_FREQUENCIES

ALLOWED_TYPES = {"expense", "income"}


def validate(inp) -> None:
    if inp.type not in ALLOWED_TYPES:
        raise ValidationError(f"invalid_recurring_rule_type: {inp.type}")
    if inp.frequency not in RECURRING_FREQUENCIES:
        raise ValidationError(f"invalid_recurring_frequency: {inp.frequency}")
    if not inp.wallet_id:
        raise ValidationError("wallet_id_required")
    if not inp.category_id:
        raise ValidationError("category_id_required")
    if not inp.merchant_name or not inp.merchant_name.strip():
        raise ValidationError("merchant_name_required")
    if not inp.next_due_date:
        raise ValidationError("next_due_date_required")
    try:
        datetime.fromisoformat(inp.next_due_date)
    except Exception as exc:
        raise ValidationError("invalid_next_due_date") from exc
    if inp.amount is not None and (not isinstance(inp.amount, (int, float)) or inp.amount <= 0):
        raise ValidationError("amount_must_be_positive_number")

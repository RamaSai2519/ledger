from datetime import datetime

from shared.output import ValidationError


def validate(inp) -> None:
    if not inp.name or not inp.name.strip():
        raise ValidationError("loan_name_required")
    if not inp.wallet_id:
        raise ValidationError("wallet_id_required")
    if not inp.category_id:
        raise ValidationError("category_id_required")
    if not isinstance(inp.principal, (int, float)) or inp.principal <= 0:
        raise ValidationError("principal_must_be_positive_number")
    if not isinstance(inp.annual_interest_rate, (int, float)) or inp.annual_interest_rate < 0:
        raise ValidationError("annual_interest_rate_must_be_non_negative_number")
    if not isinstance(inp.tenure_months, int) or inp.tenure_months <= 0:
        raise ValidationError("tenure_months_must_be_positive_integer")
    if not isinstance(inp.emi_amount, (int, float)) or inp.emi_amount <= 0:
        raise ValidationError("emi_amount_must_be_positive_number")
    if not inp.start_date:
        raise ValidationError("start_date_required")
    try:
        datetime.fromisoformat(inp.start_date)
    except Exception as exc:
        raise ValidationError("invalid_start_date") from exc

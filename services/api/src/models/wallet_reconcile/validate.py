from shared.output import ValidationError


def validate(inp) -> None:
    if not isinstance(inp.actual_balance, (int, float)):
        raise ValidationError("actual_balance_must_be_numeric")

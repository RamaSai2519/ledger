from shared.output import ValidationError


def validate(inp) -> None:
    if not inp.mobile_number:
        raise ValidationError("mobile_number_required")
    if not inp.password:
        raise ValidationError("password_required")

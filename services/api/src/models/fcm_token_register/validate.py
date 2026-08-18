from shared.output import ValidationError


def validate(inp) -> None:
    if not inp.token or not inp.token.strip():
        raise ValidationError("fcm_token_required")

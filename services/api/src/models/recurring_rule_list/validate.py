from shared.output import ValidationError


def validate(query) -> None:
    if query.is_active is not None and query.is_active.lower() not in ("true", "false"):
        raise ValidationError(f"invalid_is_active: {query.is_active}")

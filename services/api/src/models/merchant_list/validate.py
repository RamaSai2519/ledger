from shared.output import ValidationError


def validate(query) -> None:
    if query.q is not None and not query.q.strip():
        raise ValidationError("invalid_q: must not be blank")

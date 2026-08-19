from shared.output import ValidationError


def validate(query) -> None:
    if query.user_id is not None and query.user_id != "me":
        raise ValidationError(f"invalid_user_id_filter: {query.user_id}")
    if query.is_read is not None and query.is_read.lower() not in ("true", "false"):
        raise ValidationError(f"invalid_is_read: {query.is_read}")

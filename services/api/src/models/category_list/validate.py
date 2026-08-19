from shared.output import ValidationError

ALLOWED_TYPES = {"expense", "income"}


def validate(query) -> None:
    if query.include_archived is not None and query.include_archived.lower() not in ("true", "false"):
        raise ValidationError(f"invalid_include_archived: {query.include_archived}")
    if query.type is not None and query.type not in ALLOWED_TYPES:
        raise ValidationError(f"invalid_category_type: {query.type}")

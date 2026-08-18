from shared.output import ValidationError

ALLOWED_TYPES = {"expense", "income"}


def validate(inp) -> None:
    if not inp.name or not inp.name.strip():
        raise ValidationError("category_name_required")
    if inp.type not in ALLOWED_TYPES:
        raise ValidationError(f"invalid_category_type: {inp.type}")

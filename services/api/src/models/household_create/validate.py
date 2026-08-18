from shared.output import ValidationError


def validate(inp) -> None:
    if len(inp.name.strip()) == 0:
        raise ValidationError("household_name_required")

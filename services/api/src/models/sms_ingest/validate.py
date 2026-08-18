from shared.output import ValidationError


def validate(inp) -> None:
    if not inp.raw_text or not inp.raw_text.strip():
        raise ValidationError("raw_text_required")
    if not inp.sender_id or not inp.sender_id.strip():
        raise ValidationError("sender_id_required")

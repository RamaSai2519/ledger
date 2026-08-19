from shared.output import ValidationError


def validate(sms: dict) -> None:
    if sms.get("status") != "suggested":
        raise ValidationError("sms_suggestion_already_resolved")

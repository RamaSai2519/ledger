from shared.output import ValidationError

ALLOWED_TYPES = {"expense", "income"}


def validate(sms: dict, inp) -> None:
    if sms.get("status") != "suggested":
        raise ValidationError("sms_suggestion_already_resolved")

    if inp.type is not None and inp.type not in ALLOWED_TYPES:
        raise ValidationError(f"invalid_transaction_type: {inp.type}")

    if inp.amount is not None and (not isinstance(inp.amount, (int, float)) or inp.amount <= 0):
        raise ValidationError("amount_must_be_positive")

    if not inp.wallet_id and not sms.get("suggested_wallet_id"):
        raise ValidationError("wallet_id_required")

    if not inp.category_id and not sms.get("suggested_category_id"):
        raise ValidationError("category_id_required")

from shared.output import ValidationError

ALLOWED_CREATE_TYPES = {"expense", "income"}  # transfer/adjustment have their own paths


def validate(inp) -> None:
    if inp.type not in ALLOWED_CREATE_TYPES:
        raise ValidationError(f"invalid_transaction_type: {inp.type}")
    if not isinstance(inp.amount, (int, float)) or inp.amount <= 0:
        raise ValidationError("amount_must_be_positive")
    if not inp.wallet_id:
        raise ValidationError("wallet_id_required")
    if not inp.category_id:
        raise ValidationError("category_id_required")

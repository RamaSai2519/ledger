from shared.output import ValidationError


def validate(inp) -> None:
    if not inp.wallet_id or not inp.transfer_to_wallet_id:
        raise ValidationError("both_wallet_ids_required")
    if inp.wallet_id == inp.transfer_to_wallet_id:
        raise ValidationError("cannot_transfer_to_same_wallet")
    if not isinstance(inp.amount, (int, float)) or inp.amount <= 0:
        raise ValidationError("amount_must_be_positive")

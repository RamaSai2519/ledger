from shared.output import ValidationError

PATCHABLE_FIELDS = {"wallet_id", "category_id", "amount", "merchant_name", "note", "date"}
IMMUTABLE_FIELDS = {"type", "household_id", "user_id", "transfer_to_wallet_id", "source"}
EDITABLE_TXN_TYPES = {"expense", "income"}


def validate(existing_txn: dict, request_json: dict) -> dict:
    if existing_txn["type"] not in EDITABLE_TXN_TYPES:
        raise ValidationError(
            f"cannot_edit_{existing_txn['type']}_transaction_through_this_endpoint"
        )
    if not request_json:
        raise ValidationError("no_fields_to_update")

    blocked = set(request_json) & IMMUTABLE_FIELDS
    if blocked:
        raise ValidationError(f"cannot_update_fields: {sorted(blocked)}")

    updates = {k: v for k, v in request_json.items() if k in PATCHABLE_FIELDS}
    if not updates:
        raise ValidationError("no_recognized_fields_to_update")
    if "amount" in updates and (not isinstance(updates["amount"], (int, float)) or updates["amount"] <= 0):
        raise ValidationError("amount_must_be_positive")
    return updates

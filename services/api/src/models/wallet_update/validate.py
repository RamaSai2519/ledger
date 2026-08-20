from shared.output import ValidationError

PATCHABLE_FIELDS = {
    "name",
    "provider",
    "account_last4",
    "icon",
    "color",
    "is_archived",
    "credit_card_details",
    "pay_later_details",
}

IMMUTABLE_FIELDS = {"type", "opening_balance", "current_balance", "household_id", "created_by"}


def validate(request_json: dict) -> dict:
    if not request_json:
        raise ValidationError("no_fields_to_update")

    blocked = set(request_json) & IMMUTABLE_FIELDS
    if blocked:
        raise ValidationError(f"cannot_update_fields: {sorted(blocked)}")

    updates = {k: v for k, v in request_json.items() if k in PATCHABLE_FIELDS}
    if not updates:
        raise ValidationError("no_recognized_fields_to_update")
    if "name" in updates and not (updates["name"] or "").strip():
        raise ValidationError("wallet_name_required")
    return updates

from shared.output import ValidationError

# principal/outstanding_balance/start_date/annual_interest_rate/tenure_months
# are derived/immutable once a loan is created — same spirit as
# wallet_update's IMMUTABLE_FIELDS (opening_balance/current_balance/type
# can't be patched there either).
PATCHABLE_FIELDS = {
    "name",
    "emi_amount",
    "is_active",
    "wallet_id",
    "category_id",
}
IMMUTABLE_FIELDS = {
    "household_id",
    "principal",
    "outstanding_balance",
    "start_date",
    "annual_interest_rate",
    "tenure_months",
    "next_due_date",
    "created_at",
}


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
        raise ValidationError("loan_name_required")

    if "emi_amount" in updates:
        emi_amount = updates["emi_amount"]
        if not isinstance(emi_amount, (int, float)) or emi_amount <= 0:
            raise ValidationError("emi_amount_must_be_positive_number")

    return updates

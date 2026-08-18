from shared.output import ValidationError

PATCHABLE_FIELDS = {"amount", "threshold_percents"}
IMMUTABLE_FIELDS = {"scope", "scope_ref_id", "period", "household_id", "created_at"}


def validate(request_json: dict) -> dict:
    if not request_json:
        raise ValidationError("no_fields_to_update")

    blocked = set(request_json) & IMMUTABLE_FIELDS
    if blocked:
        raise ValidationError(f"cannot_update_fields: {sorted(blocked)}")

    updates = {k: v for k, v in request_json.items() if k in PATCHABLE_FIELDS}
    if not updates:
        raise ValidationError("no_recognized_fields_to_update")

    if "amount" in updates:
        amount = updates["amount"]
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError("amount_must_be_positive_number")

    if "threshold_percents" in updates:
        thresholds = updates["threshold_percents"]
        if not isinstance(thresholds, list) or not thresholds:
            raise ValidationError("threshold_percents_must_be_a_non_empty_list")
        for t in thresholds:
            if not isinstance(t, (int, float)) or t <= 0:
                raise ValidationError("threshold_percents_must_be_positive_numbers")
        updates["threshold_percents"] = sorted(thresholds)

    return updates

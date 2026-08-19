from datetime import datetime

from shared.output import ValidationError
from shared.recurring import RECURRING_FREQUENCIES

PATCHABLE_FIELDS = {
    "wallet_id",
    "category_id",
    "type",
    "merchant_name",
    "amount",
    "frequency",
    "next_due_date",
    "auto_create",
    "is_active",
}
IMMUTABLE_FIELDS = {"household_id", "auto_detected", "created_at"}
ALLOWED_TYPES = {"expense", "income"}


def validate(request_json: dict) -> dict:
    if not request_json:
        raise ValidationError("no_fields_to_update")

    blocked = set(request_json) & IMMUTABLE_FIELDS
    if blocked:
        raise ValidationError(f"cannot_update_fields: {sorted(blocked)}")

    updates = {k: v for k, v in request_json.items() if k in PATCHABLE_FIELDS}
    if not updates:
        raise ValidationError("no_recognized_fields_to_update")

    if "frequency" in updates and updates["frequency"] not in RECURRING_FREQUENCIES:
        raise ValidationError(f"invalid_recurring_frequency: {updates['frequency']}")

    if "type" in updates and updates["type"] not in ALLOWED_TYPES:
        raise ValidationError(f"invalid_recurring_rule_type: {updates['type']}")

    if "merchant_name" in updates and not (updates["merchant_name"] or "").strip():
        raise ValidationError("merchant_name_required")

    if "amount" in updates and updates["amount"] is not None:
        amount = updates["amount"]
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError("amount_must_be_positive_number")

    if "next_due_date" in updates:
        try:
            datetime.fromisoformat(updates["next_due_date"])
        except Exception as exc:
            raise ValidationError("invalid_next_due_date") from exc

    return updates

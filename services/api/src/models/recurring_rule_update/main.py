from datetime import datetime, timezone

from models.recurring_rule_update import validate
from shared.db import get_recurring_rules_collection
from shared.output import ValidationError, success
from shared.scope import get_household_category, get_household_recurring_rule, require_household_id
from shared.serializers import serialize_recurring_rule
from shared.transactions_engine import get_household_wallet


def process(rule_id: str, request_json: dict, user_id: str):
    household_id = require_household_id(user_id)
    rule = get_household_recurring_rule(household_id, rule_id)
    updates = validate.validate(request_json)

    if "wallet_id" in updates:
        wallet = get_household_wallet(household_id, updates["wallet_id"])
        updates["wallet_id"] = wallet["_id"]

    effective_type = updates.get("type", rule.get("type"))
    if "category_id" in updates or "type" in updates:
        category_id = updates["category_id"] if "category_id" in updates else str(rule["category_id"])
        category = get_household_category(household_id, category_id)
        if category.get("is_archived"):
            raise ValidationError("category_is_archived")
        if category["type"] != effective_type:
            raise ValidationError("category_type_mismatch")
        updates["category_id"] = category["_id"]

    if "next_due_date" in updates:
        updates["next_due_date"] = datetime.fromisoformat(updates["next_due_date"]).replace(tzinfo=None)

    updates["updated_at"] = datetime.now(timezone.utc)

    get_recurring_rules_collection().update_one({"_id": rule["_id"]}, {"$set": updates})
    rule.update(updates)
    return success(serialize_recurring_rule(rule))

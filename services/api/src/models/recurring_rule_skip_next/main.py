from datetime import datetime, timezone

from shared.db import get_recurring_rules_collection
from shared.output import success
from shared.recurring import advance_next_due_date
from shared.scope import get_household_recurring_rule, require_household_id
from shared.serializers import serialize_recurring_rule


def process(rule_id: str, user_id: str):
    household_id = require_household_id(user_id)
    rule = get_household_recurring_rule(household_id, rule_id)

    next_due_date = advance_next_due_date(rule["next_due_date"], rule["frequency"])
    updates = {
        "next_due_date": datetime.combine(next_due_date, datetime.min.time()),
        "updated_at": datetime.now(timezone.utc),
    }

    get_recurring_rules_collection().update_one({"_id": rule["_id"]}, {"$set": updates})
    rule.update(updates)
    return success(serialize_recurring_rule(rule))

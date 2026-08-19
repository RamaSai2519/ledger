from models.recurring_rule_list import validate
from shared.db import get_recurring_rules_collection
from shared.interfaces import RecurringRuleListInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_recurring_rule


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    mongo_query = {"household_id": household_id}
    if inp.is_active is not None:
        mongo_query["is_active"] = inp.is_active.lower() == "true"

    rules = list(get_recurring_rules_collection().find(mongo_query).sort("created_at", 1))
    return success({"recurring_rules": [serialize_recurring_rule(r) for r in rules]})

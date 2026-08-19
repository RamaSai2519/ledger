from shared.db import get_recurring_rules_collection
from shared.output import success
from shared.scope import get_household_recurring_rule, require_household_id


def process(rule_id: str, user_id: str):
    household_id = require_household_id(user_id)
    rule = get_household_recurring_rule(household_id, rule_id)

    # Transactions previously created from this rule keep their
    # recurring_rule_id reference for audit/history — deleting the rule
    # never cascades to them, mirroring how deleting a category leaves
    # existing transactions' category_id untouched (models/category_delete).
    get_recurring_rules_collection().delete_one({"_id": rule["_id"]})
    return success({"id": str(rule["_id"]), "deleted": True})

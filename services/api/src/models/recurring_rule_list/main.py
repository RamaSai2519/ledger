from shared.db import get_recurring_rules_collection
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_recurring_rule


def process(user_id: str, query_args: dict | None = None):
    query_args = query_args or {}
    household_id = require_household_id(user_id)

    query = {"household_id": household_id}
    if "is_active" in query_args:
        query["is_active"] = query_args["is_active"].lower() == "true"

    rules = list(get_recurring_rules_collection().find(query).sort("created_at", 1))
    return success({"recurring_rules": [serialize_recurring_rule(r) for r in rules]})

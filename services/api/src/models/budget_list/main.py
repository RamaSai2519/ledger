from shared.db import get_budgets_collection
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_budget


def process(user_id: str, query_args: dict | None = None):
    query_args = query_args or {}
    household_id = require_household_id(user_id)

    query = {"household_id": household_id}
    if query_args.get("scope"):
        query["scope"] = query_args["scope"]

    budgets = list(get_budgets_collection().find(query).sort("created_at", 1))
    return success({"budgets": [serialize_budget(b) for b in budgets]})

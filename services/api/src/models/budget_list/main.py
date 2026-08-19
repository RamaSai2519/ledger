from models.budget_list import validate
from shared.db import get_budgets_collection
from shared.interfaces import BudgetListInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_budget


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    mongo_query = {"household_id": household_id}
    if inp.scope:
        mongo_query["scope"] = inp.scope

    budgets = list(get_budgets_collection().find(mongo_query).sort("created_at", 1))
    return success({"budgets": [serialize_budget(b) for b in budgets]})

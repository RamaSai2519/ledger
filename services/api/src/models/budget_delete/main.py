from shared.db import get_budgets_collection
from shared.output import success
from shared.scope import get_household_budget, require_household_id


def process(budget_id: str, user_id: str):
    household_id = require_household_id(user_id)
    budget = get_household_budget(household_id, budget_id)

    get_budgets_collection().delete_one({"_id": budget["_id"]})
    return success({"id": str(budget["_id"]), "deleted": True})

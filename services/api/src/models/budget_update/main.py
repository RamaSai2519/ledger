from datetime import datetime, timezone

from models.budget_update import validate
from shared.db import get_budgets_collection
from shared.interfaces import BudgetUpdateInput as Input
from shared.output import success
from shared.scope import get_household_budget, require_household_id
from shared.serializers import serialize_budget


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    budget = get_household_budget(household_id, inp.budget_id)
    updates = validate.validate(inp.body)
    updates["updated_at"] = datetime.now(timezone.utc)

    get_budgets_collection().update_one({"_id": budget["_id"]}, {"$set": updates})
    budget.update(updates)
    return success(serialize_budget(budget))

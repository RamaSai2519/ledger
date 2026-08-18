from shared.budgets import compute_budget_progress
from shared.output import success
from shared.scope import get_household_budget, require_household_id
from shared.serializers import serialize_budget_progress


def process(budget_id: str, user_id: str):
    household_id = require_household_id(user_id)
    budget = get_household_budget(household_id, budget_id)
    progress = compute_budget_progress(household_id, budget)
    return success(serialize_budget_progress(progress))

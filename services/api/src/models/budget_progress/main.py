from shared.budgets import compute_budget_progress
from shared.interfaces import BudgetProgressInput as Input
from shared.output import success
from shared.scope import get_household_budget, require_household_id
from shared.serializers import serialize_budget_progress


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    budget = get_household_budget(household_id, inp.budget_id)
    progress = compute_budget_progress(household_id, budget)
    return success(serialize_budget_progress(progress))

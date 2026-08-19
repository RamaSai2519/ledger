from models.budget_create import compute, validate
from shared.interfaces import BudgetCreateInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_budget


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)
    budget = compute.create_budget(inp, household_id)
    return success(serialize_budget(budget))

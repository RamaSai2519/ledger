from models.insight_income_vs_expense import compute, validate
from shared.interfaces import InsightIncomeVsExpenseInput as Input
from shared.output import success
from shared.scope import require_household_id


def process(inp: Input):
    period = validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    result = compute.get_income_vs_expense(household_id, period, inp.from_, inp.to)
    return success(result)

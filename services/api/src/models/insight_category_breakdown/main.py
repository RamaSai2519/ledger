from models.insight_category_breakdown import compute, validate
from shared.interfaces import InsightCategoryBreakdownInput as Input
from shared.output import success
from shared.scope import require_household_id


def process(inp: Input):
    period = validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    result = compute.get_category_breakdown(household_id, period, inp.from_, inp.to)
    return success(result)

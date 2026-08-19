from models.insight_trends import compute, validate
from shared.interfaces import InsightTrendsInput as Input
from shared.output import success
from shared.scope import require_household_id


def process(inp: Input):
    period = validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    result = compute.get_trends(household_id, period, inp.from_, inp.to)
    return success(result)

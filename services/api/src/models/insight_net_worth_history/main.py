from models.insight_net_worth_history import compute, validate
from shared.interfaces import InsightNetWorthHistoryInput as Input
from shared.output import success
from shared.scope import require_household_id


def process(inp: Input):
    from_date, to_date = validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    result = compute.get_net_worth_history(household_id, from_date, to_date)
    return success(result)

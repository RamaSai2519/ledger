from models.insight_category_breakdown import compute, validate
from shared.output import success
from shared.scope import require_household_id


def process(user_id: str, query_args: dict | None = None):
    query_args = query_args or {}
    period = validate.validate(query_args.get("period"))
    household_id = require_household_id(user_id)

    result = compute.get_category_breakdown(household_id, period, query_args.get("from"), query_args.get("to"))
    return success(result)

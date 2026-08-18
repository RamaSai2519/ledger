from models.insight_net_worth_history import compute, validate
from shared.output import success
from shared.scope import require_household_id


def process(user_id: str, query_args: dict | None = None):
    query_args = query_args or {}
    from_date, to_date = validate.validate(query_args.get("from"), query_args.get("to"))
    household_id = require_household_id(user_id)

    result = compute.get_net_worth_history(household_id, from_date, to_date)
    return success(result)

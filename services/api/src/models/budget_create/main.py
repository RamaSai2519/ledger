from dataclasses import dataclass

from models.budget_create import compute, validate
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_budget


@dataclass
class Input:
    scope: str
    amount: float
    scope_ref_id: str | None = None
    period: str = "monthly"
    threshold_percents: list | None = None


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    household_id = require_household_id(user_id)
    budget = compute.create_budget(inp, household_id)
    return success(serialize_budget(budget))

from dataclasses import dataclass

from models.recurring_rule_create import compute, validate
from shared.output import success
from shared.serializers import serialize_recurring_rule


@dataclass
class Input:
    wallet_id: str
    category_id: str
    type: str
    merchant_name: str
    frequency: str
    next_due_date: str
    amount: float | None = None
    auto_create: bool = False
    is_active: bool = True


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    rule = compute.create_recurring_rule(inp, user_id)
    return success(serialize_recurring_rule(rule))

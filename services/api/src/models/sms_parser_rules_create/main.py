from dataclasses import dataclass, field

from models.sms_parser_rules_create import compute, validate
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_sms_parser_rule


@dataclass
class Input:
    bank_code: str
    sender_ids: list = field(default_factory=list)
    patterns: list = field(default_factory=list)
    is_active: bool = True


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    household_id = require_household_id(user_id)
    rule = compute.create_parser_rule(inp, household_id)
    return success(serialize_sms_parser_rule(rule))

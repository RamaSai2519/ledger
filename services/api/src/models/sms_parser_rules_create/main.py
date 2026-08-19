from models.sms_parser_rules_create import compute, validate
from shared.interfaces import SmsParserRulesCreateInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_sms_parser_rule


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)
    rule = compute.create_parser_rule(inp, household_id)
    return success(serialize_sms_parser_rule(rule))

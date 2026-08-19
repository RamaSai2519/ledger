from models.recurring_rule_create import compute, validate
from shared.interfaces import RecurringRuleCreateInput as Input
from shared.output import success
from shared.serializers import serialize_recurring_rule


def process(inp: Input):
    validate.validate(inp)
    rule = compute.create_recurring_rule(inp, inp.user_id)
    return success(serialize_recurring_rule(rule))


from models.sms_suggestion_dismiss import compute, validate
from shared.interfaces import SmsSuggestionDismissInput as Input
from shared.output import success
from shared.scope import get_household_sms_suggestion, require_household_id
from shared.serializers import serialize_sms_inbox


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    sms = get_household_sms_suggestion(household_id, inp.sms_id)
    validate.validate(sms)
    doc = compute.dismiss_suggestion(sms)
    return success(serialize_sms_inbox(doc))

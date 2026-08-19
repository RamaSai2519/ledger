from models.sms_suggestion_accept import compute, validate
from shared.interfaces import SmsSuggestionAcceptInput as Input
from shared.output import success
from shared.scope import get_household_sms_suggestion, require_household_id
from shared.serializers import serialize_transaction


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    sms = get_household_sms_suggestion(household_id, inp.sms_id)
    validate.validate(sms, inp)
    txn = compute.accept_suggestion(sms, inp, household_id, inp.user_id)
    return success(serialize_transaction(txn))

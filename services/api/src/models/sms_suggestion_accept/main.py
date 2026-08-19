from dataclasses import dataclass

from models.sms_suggestion_accept import compute, validate
from shared.output import success
from shared.scope import get_household_sms_suggestion, require_household_id
from shared.serializers import serialize_transaction


@dataclass
class Input:
    wallet_id: str | None = None
    category_id: str | None = None
    amount: float | None = None
    type: str | None = None
    date: str | None = None


def process(sms_id: str, request_json: dict, user_id: str):
    inp = Input(**(request_json or {}))
    household_id = require_household_id(user_id)
    sms = get_household_sms_suggestion(household_id, sms_id)
    validate.validate(sms, inp)
    txn = compute.accept_suggestion(sms, inp, household_id, user_id)
    return success(serialize_transaction(txn))

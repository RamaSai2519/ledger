from dataclasses import dataclass

from models.transaction_transfer import compute, validate
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_transaction


@dataclass
class Input:
    wallet_id: str
    transfer_to_wallet_id: str
    amount: float
    note: str | None = None
    date: str | None = None


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)

    household_id = require_household_id(user_id)
    txn = compute.create_transfer(inp, user_id, household_id)
    return success(serialize_transaction(txn))

from dataclasses import dataclass

from models.transaction_create import compute, validate
from shared.output import success
from shared.serializers import serialize_transaction


@dataclass
class Input:
    wallet_id: str
    category_id: str
    type: str
    amount: float
    merchant_name: str | None = None
    note: str | None = None
    date: str | None = None


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    txn = compute.create_transaction(inp, user_id)
    return success(serialize_transaction(txn))

from dataclasses import dataclass

from models.wallet_create import compute, validate
from shared.output import success
from shared.serializers import serialize_wallet


@dataclass
class Input:
    name: str
    type: str
    provider: str | None = None
    account_last4: str | None = None
    opening_balance: float = 0
    currency: str = "INR"
    icon: str | None = None
    color: str | None = None
    credit_card_details: dict | None = None
    pay_later_details: dict | None = None
    loan_details: dict | None = None


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    wallet = compute.create_wallet(inp, user_id)
    return success(serialize_wallet(wallet))

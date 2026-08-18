from dataclasses import dataclass

from models.wallet_reconcile import compute, validate
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_transaction, serialize_wallet
from shared.transactions_engine import get_household_wallet


@dataclass
class Input:
    actual_balance: float


def process(wallet_id: str, request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)

    household_id = require_household_id(user_id)
    wallet = get_household_wallet(household_id, wallet_id)

    result = compute.reconcile_wallet(household_id, wallet, inp.actual_balance, user_id)
    return success(
        {
            "wallet": serialize_wallet(result["wallet"]),
            "adjustment_transaction": serialize_transaction(result["transaction"]),
            "delta": result["delta"],
        }
    )

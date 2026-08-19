from models.wallet_reconcile import compute, validate
from shared.interfaces import WalletReconcileInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_transaction, serialize_wallet
from shared.transactions_engine import get_household_wallet


def process(inp: Input):
    validate.validate(inp)

    household_id = require_household_id(inp.user_id)
    wallet = get_household_wallet(household_id, inp.wallet_id)

    result = compute.reconcile_wallet(household_id, wallet, inp.actual_balance, inp.user_id)
    return success(
        {
            "wallet": serialize_wallet(result["wallet"]),
            "adjustment_transaction": serialize_transaction(result["transaction"]),
            "delta": result["delta"],
        }
    )

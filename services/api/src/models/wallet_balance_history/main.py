from models.wallet_balance_history import compute, validate
from shared.interfaces import WalletBalanceHistoryInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.transactions_engine import get_household_wallet


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)
    wallet = get_household_wallet(household_id, inp.wallet_id)

    points = compute.get_balance_history(wallet, inp.from_, inp.to)
    return success({"wallet_id": str(wallet["_id"]), "points": points})

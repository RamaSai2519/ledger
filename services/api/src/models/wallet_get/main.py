from shared.interfaces import WalletGetInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_wallet
from shared.transactions_engine import get_household_wallet


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    wallet = get_household_wallet(household_id, inp.wallet_id)
    return success(serialize_wallet(wallet))

from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_wallet
from shared.transactions_engine import get_household_wallet


def process(wallet_id: str, user_id: str):
    household_id = require_household_id(user_id)
    wallet = get_household_wallet(household_id, wallet_id)
    return success(serialize_wallet(wallet))

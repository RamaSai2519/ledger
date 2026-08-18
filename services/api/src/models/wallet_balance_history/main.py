from models.wallet_balance_history import compute
from shared.output import success
from shared.scope import require_household_id
from shared.transactions_engine import get_household_wallet


def process(wallet_id: str, user_id: str, query_args: dict | None = None):
    query_args = query_args or {}
    household_id = require_household_id(user_id)
    wallet = get_household_wallet(household_id, wallet_id)

    points = compute.get_balance_history(wallet, query_args.get("from"), query_args.get("to"))
    return success({"wallet_id": str(wallet["_id"]), "points": points})

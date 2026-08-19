from datetime import datetime, timezone

from models.wallet_update import validate
from shared.db import get_wallets_collection
from shared.interfaces import WalletUpdateInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_wallet
from shared.transactions_engine import get_household_wallet


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    wallet = get_household_wallet(household_id, inp.wallet_id)
    updates = validate.validate(inp.body)
    updates["updated_at"] = datetime.now(timezone.utc)

    get_wallets_collection().update_one({"_id": wallet["_id"]}, {"$set": updates})
    wallet.update(updates)
    return success(serialize_wallet(wallet))

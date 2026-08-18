from datetime import datetime, timezone

from shared.db import get_wallets_collection
from shared.output import success
from shared.scope import require_household_id
from shared.transactions_engine import get_household_wallet


def process(wallet_id: str, user_id: str):
    household_id = require_household_id(user_id)
    wallet = get_household_wallet(household_id, wallet_id)

    # Wallets are never hard-deleted — they're referenced by transaction
    # history, which must stay intact for audit/reporting even after a
    # wallet is retired. DELETE archives instead.
    get_wallets_collection().update_one(
        {"_id": wallet["_id"]}, {"$set": {"is_archived": True, "updated_at": datetime.now(timezone.utc)}}
    )
    return success({"id": str(wallet["_id"]), "is_archived": True})

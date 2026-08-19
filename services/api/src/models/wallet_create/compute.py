from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_wallets_collection
from shared.scope import require_household_id


def create_wallet(inp, user_id: str) -> dict:
    household_id = require_household_id(user_id)
    now = datetime.now(timezone.utc)

    doc = {
        "household_id": household_id,
        "name": inp.name.strip(),
        "type": inp.type,
        "provider": inp.provider,
        "account_last4": inp.account_last4,
        "opening_balance": inp.opening_balance,
        "current_balance": inp.opening_balance,
        "currency": inp.currency,
        "icon": inp.icon,
        "color": inp.color,
        "is_archived": False,
        "credit_card_details": inp.credit_card_details,
        "pay_later_details": inp.pay_later_details,
        # loan_details has no create-path Input field — "loan" isn't a
        # creatable wallet type any more (shared/balance.py's
        # CREATABLE_WALLET_TYPES), only still supported on pre-existing loan
        # wallets via wallet_update. Kept here so every wallet doc has the
        # same shape.
        "loan_details": None,
        "created_by": ObjectId(user_id),
        "created_at": now,
        "updated_at": now,
    }
    result = get_wallets_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

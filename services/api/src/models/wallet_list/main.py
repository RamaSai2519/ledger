from models.wallet_list import validate
from shared.db import get_wallets_collection
from shared.interfaces import WalletListInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_wallet


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    mongo_query = {"household_id": household_id}
    if (inp.include_archived or "false").lower() != "true":
        mongo_query["is_archived"] = {"$ne": True}
    if inp.type:
        mongo_query["type"] = inp.type

    wallets = list(get_wallets_collection().find(mongo_query).sort("created_at", 1))
    return success({"wallets": [serialize_wallet(w) for w in wallets]})

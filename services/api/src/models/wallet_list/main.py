from shared.db import get_wallets_collection
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_wallet


def process(user_id: str, query_args: dict | None = None):
    query_args = query_args or {}
    household_id = require_household_id(user_id)

    query = {"household_id": household_id}
    if query_args.get("include_archived", "false").lower() != "true":
        query["is_archived"] = {"$ne": True}
    if query_args.get("type"):
        query["type"] = query_args["type"]

    wallets = list(get_wallets_collection().find(query).sort("created_at", 1))
    return success({"wallets": [serialize_wallet(w) for w in wallets]})

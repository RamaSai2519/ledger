from shared.db import get_categories_collection
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_category


def process(user_id: str, query_args: dict | None = None):
    query_args = query_args or {}
    household_id = require_household_id(user_id)

    query = {"household_id": household_id}
    if query_args.get("include_archived", "false").lower() != "true":
        query["is_archived"] = {"$ne": True}
    if query_args.get("type"):
        query["type"] = query_args["type"]

    categories = list(get_categories_collection().find(query).sort("name", 1))
    return success({"categories": [serialize_category(c) for c in categories]})

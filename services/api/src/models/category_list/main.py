from models.category_list import validate
from shared.db import get_categories_collection
from shared.interfaces import CategoryListInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_category


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    mongo_query = {"household_id": household_id}
    if (inp.include_archived or "false").lower() != "true":
        mongo_query["is_archived"] = {"$ne": True}
    if inp.type:
        mongo_query["type"] = inp.type

    categories = list(get_categories_collection().find(mongo_query).sort([("sort_order", 1), ("name", 1)]))
    return success({"categories": [serialize_category(c) for c in categories]})

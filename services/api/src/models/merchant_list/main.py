import re

from models.merchant_list import validate
from shared.db import get_merchant_alias_collection
from shared.interfaces import MerchantListInput as Input
from shared.output import success
from shared.scope import require_household_id


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    query = {"$or": [{"household_id": household_id}, {"household_id": None}]}
    if inp.q:
        query["canonical_name"] = {"$regex": re.escape(inp.q.strip()), "$options": "i"}

    collection = get_merchant_alias_collection()
    names = sorted({doc["canonical_name"] for doc in collection.find(query, {"canonical_name": 1})})
    return success({"merchants": names})

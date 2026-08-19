from datetime import datetime

from bson import ObjectId

from models.transaction_list import validate
from shared.db import get_transactions_collection
from shared.interfaces import TransactionListInput as Input
from shared.output import ValidationError, success
from shared.pagination import parse_pagination
from shared.scope import require_household_id
from shared.serializers import serialize_transaction


def _to_object_id(value: str, field: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:
        raise ValidationError(f"invalid_{field}") from exc


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.requesting_user_id)

    mongo_query: dict = {"household_id": household_id}
    if inp.wallet_id:
        mongo_query["wallet_id"] = _to_object_id(inp.wallet_id, "wallet_id")
    if inp.category_id:
        mongo_query["category_id"] = _to_object_id(inp.category_id, "category_id")
    if inp.user_id:
        mongo_query["user_id"] = _to_object_id(inp.user_id, "user_id")
    if inp.type:
        mongo_query["type"] = inp.type

    date_filter = {}
    if inp.from_:
        date_filter["$gte"] = datetime.fromisoformat(inp.from_)
    if inp.to:
        date_filter["$lte"] = datetime.fromisoformat(inp.to)
    if date_filter:
        mongo_query["date"] = date_filter

    page, page_size = parse_pagination(inp)

    collection = get_transactions_collection()
    total = collection.count_documents(mongo_query)
    cursor = collection.find(mongo_query).sort("date", -1).skip((page - 1) * page_size).limit(page_size)
    transactions = [serialize_transaction(t) for t in cursor]

    return success(
        {
            "transactions": transactions,
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": page * page_size < total,
        }
    )

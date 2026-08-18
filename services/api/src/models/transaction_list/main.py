from datetime import datetime

from bson import ObjectId

from shared.db import get_transactions_collection
from shared.output import ValidationError, success
from shared.scope import require_household_id
from shared.serializers import serialize_transaction


def _to_object_id(value: str, field: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:
        raise ValidationError(f"invalid_{field}") from exc


def process(user_id: str, query_args: dict | None = None):
    query_args = query_args or {}
    household_id = require_household_id(user_id)

    query: dict = {"household_id": household_id}
    if query_args.get("wallet_id"):
        query["wallet_id"] = _to_object_id(query_args["wallet_id"], "wallet_id")
    if query_args.get("category_id"):
        query["category_id"] = _to_object_id(query_args["category_id"], "category_id")
    if query_args.get("user_id"):
        query["user_id"] = _to_object_id(query_args["user_id"], "user_id")
    if query_args.get("type"):
        query["type"] = query_args["type"]

    date_filter = {}
    if query_args.get("from"):
        date_filter["$gte"] = datetime.fromisoformat(query_args["from"])
    if query_args.get("to"):
        date_filter["$lte"] = datetime.fromisoformat(query_args["to"])
    if date_filter:
        query["date"] = date_filter

    try:
        page = max(1, int(query_args.get("page", 1)))
        page_size = min(100, max(1, int(query_args.get("page_size", 20))))
    except ValueError as exc:
        raise ValidationError("invalid_pagination_params") from exc

    collection = get_transactions_collection()
    total = collection.count_documents(query)
    cursor = collection.find(query).sort("date", -1).skip((page - 1) * page_size).limit(page_size)
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

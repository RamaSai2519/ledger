from bson import ObjectId

from shared.db import get_categories_collection
from shared.output import ValidationError
from shared.serializers import serialize_category
from shared.transactions_engine import _run_atomically


def reorder_categories(inp, household_id: ObjectId) -> list[dict]:
    categories = get_categories_collection()

    try:
        oids = [ObjectId(cid) for cid in inp.order]
    except Exception as exc:
        raise ValidationError("invalid_category_id") from exc

    matched = list(categories.find({"_id": {"$in": oids}, "household_id": household_id}))
    if len(matched) != len(oids):
        raise ValidationError("category_not_in_household")

    def _do(session):
        for i, oid in enumerate(oids):
            categories.update_one({"_id": oid}, {"$set": {"sort_order": i}}, session=session)

    _run_atomically(_do)

    reordered = list(categories.find({"household_id": household_id}).sort([("sort_order", 1), ("name", 1)]))
    return [serialize_category(c) for c in reordered]

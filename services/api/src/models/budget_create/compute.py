from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_budgets_collection
from shared.output import ValidationError
from shared.scope import get_household_category
from shared.transactions_engine import get_household_wallet


def _resolve_scope_ref_id(inp, household_id: ObjectId) -> ObjectId | None:
    if inp.scope == "category":
        category = get_household_category(household_id, inp.scope_ref_id)
        return category["_id"]
    if inp.scope == "wallet":
        wallet = get_household_wallet(household_id, inp.scope_ref_id)
        return wallet["_id"]
    return None


def create_budget(inp, household_id: ObjectId) -> dict:
    scope_ref_id = _resolve_scope_ref_id(inp, household_id)
    now = datetime.now(timezone.utc)

    doc = {
        "household_id": household_id,
        "scope": inp.scope,
        "scope_ref_id": scope_ref_id,
        "amount": inp.amount,
        "period": inp.period,
        "threshold_percents": sorted(inp.threshold_percents) if inp.threshold_percents else [80, 100],
        "created_at": now,
        "updated_at": now,
    }
    result = get_budgets_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

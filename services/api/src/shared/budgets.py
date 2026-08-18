"""Budget progress computation (plan.md §8), shared by the GET
/budgets/:id/progress endpoint and jobs/budget_threshold_check.py so the two
never compute "how much has been spent against this budget" differently.

Progress = sum of `expense` transactions in the current calendar month
matching the budget's scope:
- scope == "category": transactions with category_id == scope_ref_id
- scope == "wallet": transactions with wallet_id == scope_ref_id
- scope == "overall": all expense transactions household-wide
"""
from calendar import monthrange
from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_transactions_collection


def current_month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    last_day = monthrange(now.year, now.month)[1]
    end = datetime(now.year, now.month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    return start, end


def _scope_query(household_id: ObjectId, budget: dict) -> dict:
    query: dict = {"household_id": household_id, "type": "expense"}
    scope = budget["scope"]
    if scope == "category":
        query["category_id"] = budget["scope_ref_id"]
    elif scope == "wallet":
        query["wallet_id"] = budget["scope_ref_id"]
    elif scope != "overall":
        raise ValueError(f"unsupported_budget_scope: {scope}")
    return query


def compute_budget_progress(household_id: ObjectId, budget: dict, now: datetime | None = None) -> dict:
    start, end = current_month_bounds(now)
    query = _scope_query(household_id, budget)
    query["date"] = {"$gte": start, "$lte": end}

    spent = 0.0
    for txn in get_transactions_collection().find(query):
        spent += txn.get("amount", 0)

    amount = budget.get("amount", 0) or 0
    percent = (spent / amount * 100) if amount else 0.0
    thresholds = budget.get("threshold_percents") or [80, 100]
    crossed = sorted(t for t in thresholds if percent >= t)

    return {
        "budget_id": budget["_id"],
        "spent": spent,
        "amount": amount,
        "percent": round(percent, 2),
        "period_start": start,
        "period_end": end,
        "thresholds": sorted(thresholds),
        "crossed_thresholds": crossed,
    }

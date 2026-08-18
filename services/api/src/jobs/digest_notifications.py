"""Daily/weekly digest notification job (plan.md §8, LED-5).

See jobs/budget_threshold_check.py's module docstring for why this is a
plain callable function dispatched via EventBridge Scheduler rather than
APScheduler (docs/decisions/0005-eventbridge-scheduler-for-jobs.md).

For every household, summarizes spend so far this calendar month, the top
spending category, and days left in the month, and fires a `digest`
notification regardless of budget threshold status (plan.md §8: "Digest —
a daily or weekly summary notification... regardless of threshold status").
"""
import logging
from calendar import monthrange
from datetime import datetime, timezone

from shared.budgets import current_month_bounds
from shared.db import get_categories_collection, get_households_collection, get_transactions_collection
from shared.notify import notify_household

logger = logging.getLogger(__name__)


def _days_left_in_month(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    last_day = monthrange(now.year, now.month)[1]
    return last_day - now.day


def _household_digest(household_id) -> dict:
    start, end = current_month_bounds()
    query = {"household_id": household_id, "type": "expense", "date": {"$gte": start, "$lte": end}}

    total_spent = 0.0
    by_category: dict = {}
    for txn in get_transactions_collection().find(query):
        amount = txn.get("amount", 0)
        total_spent += amount
        category_id = txn.get("category_id")
        if category_id is not None:
            by_category[category_id] = by_category.get(category_id, 0) + amount

    top_category_name = None
    top_category_amount = 0.0
    if by_category:
        top_category_id, top_category_amount = max(by_category.items(), key=lambda kv: kv[1])
        category = get_categories_collection().find_one({"_id": top_category_id})
        top_category_name = category["name"] if category else None

    return {
        "total_spent": total_spent,
        "top_category": top_category_name,
        "top_category_amount": top_category_amount,
        "days_left": _days_left_in_month(),
    }


def run_daily_digest() -> list[dict]:
    """Returns a list of {household_id, digest} sent in this run."""
    sent = []

    for household in get_households_collection().find({}):
        household_id = household["_id"]
        try:
            digest = _household_digest(household_id)
        except Exception:
            logger.exception("failed to compute digest for household_id=%s", household_id)
            continue

        title = "Your spending digest"
        top = f" — top: {digest['top_category']}" if digest["top_category"] else ""
        body = f"Spent so far this month: {digest['total_spent']:.2f}{top}. {digest['days_left']} days left."

        notify_household(household_id, "digest", digest, title, body)
        sent.append({"household_id": household_id, "digest": digest})

    return sent

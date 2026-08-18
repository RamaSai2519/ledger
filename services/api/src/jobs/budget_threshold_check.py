"""Budget threshold-crossing job (plan.md §8, LED-5).

Not wired to an in-process scheduler — this backend is a zip-deployed AWS
Lambda behind API Gateway (see index.py's `handler`), which only runs
during a request; an in-process APScheduler would never fire. Instead this
is a plain, directly-callable, unit-testable function, invoked by
index.py's `scheduled_handler` on an EventBridge Scheduler trigger — see
docs/decisions/0005-eventbridge-scheduler-for-jobs.md for the full
rationale (deviates from plan.md's literal "APScheduler for MVP" wording).

For every budget, computes progress via shared.budgets.compute_budget_progress
(the same function GET /budgets/:id/progress uses, so the endpoint and this
job never disagree) and fires a notification for each threshold_percent
crossed that hasn't already been notified this calendar month.

Dedup strategy: rather than adding a `notified_thresholds` field to the
budget doc (which would need its own monthly-reset bookkeeping), this
queries the `notifications` collection directly for an existing
budget_threshold/budget_exceeded notification with matching
payload.budget_id + payload.threshold created within the current month's
bounds. Slightly more expensive per threshold check, but stateless — no
extra field to keep in sync or reset at month boundary, and the
`notifications` collection is already the source of truth for "was this
sent."
"""
import logging

from bson import ObjectId

from shared.budgets import compute_budget_progress, current_month_bounds
from shared.db import get_budgets_collection, get_notifications_collection
from shared.notify import notify_household

logger = logging.getLogger(__name__)


def _already_notified(household_id: ObjectId, budget_id: ObjectId, threshold: float) -> bool:
    start, end = current_month_bounds()
    return (
        get_notifications_collection().find_one(
            {
                "household_id": household_id,
                "type": {"$in": ["budget_threshold", "budget_exceeded"]},
                "payload.budget_id": str(budget_id),
                "payload.threshold": threshold,
                "created_at": {"$gte": start, "$lte": end},
            }
        )
        is not None
    )


def run_budget_threshold_check() -> list[dict]:
    """Returns a list of {budget_id, threshold, notified} entries for every
    threshold newly crossed and notified in this run."""
    fired = []

    for budget in get_budgets_collection().find({}):
        household_id = budget["household_id"]
        try:
            progress = compute_budget_progress(household_id, budget)
        except Exception:
            logger.exception("failed to compute progress for budget_id=%s", budget["_id"])
            continue

        for threshold in progress["crossed_thresholds"]:
            if _already_notified(household_id, budget["_id"], threshold):
                continue

            notif_type = "budget_exceeded" if threshold >= 100 else "budget_threshold"
            payload = {
                "budget_id": str(budget["_id"]),
                "scope": budget["scope"],
                "threshold": threshold,
                "spent": progress["spent"],
                "amount": progress["amount"],
                "percent": progress["percent"],
            }
            title = "Budget exceeded" if threshold >= 100 else "Budget alert"
            body = f"You've used {progress['percent']:.0f}% of your {budget['scope']} budget."

            notify_household(household_id, notif_type, payload, title, body)
            fired.append({"budget_id": budget["_id"], "threshold": threshold, "notified": True})

    return fired

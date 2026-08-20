"""Bill due-date reminder job (plan.md §8, LED-5).

See jobs/budget_threshold_check.py's module docstring for why this is a
plain callable function dispatched via EventBridge Scheduler rather than
APScheduler (docs/decisions/0005-eventbridge-scheduler-for-jobs.md).

Scans wallets of type credit_card/pay_later whose due_day falls within
the next `bill_due_reminder_days` (default 3, shared.configs CONFIG) days,
and fires a `bill_due` notification per wallet — guarded against
re-notifying the same due date twice.

Loans no longer live as a wallet type (LED-14 moved them to their own
`loans` collection) — their due-date reminders are handled by
jobs/loan_emi_check.py, which pays the EMI directly rather than just
reminding, since loans/recurring rules have next_due_date tracked
precisely instead of a generic due_day.
"""
import logging
from calendar import monthrange
from datetime import date, datetime, timezone

from bson import ObjectId

from shared.configs import CONFIG
from shared.db import get_notifications_collection, get_wallets_collection
from shared.notify import notify_household

logger = logging.getLogger(__name__)

DUE_DAY_WALLET_TYPES = ("credit_card", "pay_later")
DETAIL_FIELD_BY_TYPE = {
    "credit_card": "credit_card_details",
    "pay_later": "pay_later_details",
}


def _next_due_date(due_day: int, today: date) -> date:
    last_day_this_month = monthrange(today.year, today.month)[1]
    day = min(due_day, last_day_this_month)
    candidate = date(today.year, today.month, day)
    if candidate < today:
        year, month = today.year, today.month + 1
        if month > 12:
            year, month = year + 1, 1
        last_day_next_month = monthrange(year, month)[1]
        candidate = date(year, month, min(due_day, last_day_next_month))
    return candidate


def _already_notified(household_id: ObjectId, wallet_id: ObjectId, due_date: date) -> bool:
    return (
        get_notifications_collection().find_one(
            {
                "household_id": household_id,
                "type": "bill_due",
                "payload.wallet_id": str(wallet_id),
                "payload.due_date": due_date.isoformat(),
            }
        )
        is not None
    )


def run_bill_due_reminders(today: date | None = None) -> list[dict]:
    """Returns a list of {wallet_id, due_date, notified} for every wallet
    reminder fired in this run."""
    today = today or datetime.now(timezone.utc).date()
    reminder_days = CONFIG["bill_due_reminder_days"]
    fired = []

    query = {"type": {"$in": DUE_DAY_WALLET_TYPES}, "is_archived": {"$ne": True}}
    for wallet in get_wallets_collection().find(query):
        detail_field = DETAIL_FIELD_BY_TYPE[wallet["type"]]
        details = wallet.get(detail_field) or {}
        due_day = details.get("due_day")
        if not due_day:
            continue

        try:
            due_date = _next_due_date(int(due_day), today)
        except Exception:
            logger.exception("failed to compute due date for wallet_id=%s", wallet["_id"])
            continue

        days_until = (due_date - today).days
        if not (0 <= days_until <= reminder_days):
            continue

        household_id = wallet["household_id"]
        if _already_notified(household_id, wallet["_id"], due_date):
            continue

        payload = {
            "wallet_id": str(wallet["_id"]),
            "wallet_name": wallet.get("name"),
            "due_date": due_date.isoformat(),
            "days_until": days_until,
        }
        title = "Bill due soon"
        body = f"{wallet.get('name')} is due on {due_date.isoformat()}."

        notify_household(household_id, "bill_due", payload, title, body)
        fired.append({"wallet_id": wallet["_id"], "due_date": due_date, "notified": True})

    return fired

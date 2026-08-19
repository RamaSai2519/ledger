"""Recurring transaction due-date job (plan.md §10, LED-8).

See jobs/budget_threshold_check.py's module docstring for why this is a
plain callable function dispatched via EventBridge Scheduler rather than
APScheduler (docs/decisions/0005-eventbridge-scheduler-for-jobs.md).

For every is_active=true recurring_rules doc whose next_due_date has
arrived (<= today):
  - If auto_create=true AND the rule has a fixed amount, auto-creates the
    transaction via shared.transactions_engine.create_single_wallet_transaction
    (the single write path for anything touching a wallet's cached
    current_balance — never a raw insert/$inc here) dated to the rule's
    next_due_date (not "now"), with source="manual" and recurring_rule_id
    set, then sends nothing further.
  - Otherwise (auto_create=false, OR amount is None because it "varies"
    cycle to cycle and there's no amount to auto-create with — this
    overrides auto_create regardless of its value, logged below so it's
    visible why a nominally auto_create rule didn't auto-create), sends a
    "recurring_reminder" notification via shared.notify.notify_household
    instead.
  - Either way, advances next_due_date by exactly one cycle afterward using
    shared.recurring.advance_next_due_date — the same helper
    models/recurring_rule_skip_next uses, so the two paths can never drift
    apart on cycle math. This always happens once a due rule is processed,
    so it doesn't re-fire every day until the user manually confirms.

Transaction attribution: recurring_rules doesn't record which household
member created the rule (plan.md §4 schema has no such field), and
user_id on a transaction is attribution-only, not an access-control field
(see plan.md §4 transactions table) — so a job-created transaction is
attributed to an arbitrary household member (the first one returned) since
there's no better signal available.
"""
import logging
from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_recurring_rules_collection
from shared.notify import get_household_members, notify_household
from shared.recurring import advance_next_due_date
from shared.transactions_engine import create_single_wallet_transaction, get_household_wallet

logger = logging.getLogger(__name__)


def _attribution_user_id(household_id: ObjectId) -> ObjectId | None:
    members = get_household_members(household_id)
    return members[0]["_id"] if members else None


def run_recurring_transactions_check(today: "datetime | None" = None) -> list[dict]:
    """Returns a list of {rule_id, action, transaction_id} entries for every
    due rule processed in this run. action is "auto_created" or
    "reminder_sent". `next_due_date` is stored as a naive datetime
    (matching models/recurring_rule_create's parsing of a date-only ISO
    string), so `today` is normalized to naive UTC here too — comparing a
    naive Mongo-stored value against an aware one raises in real pymongo."""
    today = (today or datetime.now(timezone.utc)).replace(tzinfo=None)
    processed = []

    query = {"is_active": True, "next_due_date": {"$lte": today}}
    for rule in get_recurring_rules_collection().find(query):
        household_id = rule["household_id"]
        rule_id = rule["_id"]

        try:
            action, transaction_id = _process_rule(rule, household_id)
        except Exception:
            logger.exception("failed to process recurring rule_id=%s", rule_id)
            continue

        next_due_date = advance_next_due_date(rule["next_due_date"], rule["frequency"])
        get_recurring_rules_collection().update_one(
            {"_id": rule_id},
            {
                "$set": {
                    "next_due_date": datetime.combine(next_due_date, datetime.min.time()),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        processed.append({"rule_id": rule_id, "action": action, "transaction_id": transaction_id})

    return processed


def _process_rule(rule: dict, household_id: ObjectId):
    if rule.get("auto_create") and rule.get("amount") is not None:
        transaction_id = _auto_create_transaction(rule, household_id)
        return "auto_created", transaction_id

    if rule.get("auto_create") and rule.get("amount") is None:
        logger.info(
            "recurring rule_id=%s has auto_create=true but amount is None ('varies') — "
            "sending a reminder instead since there's no amount to auto-create with",
            rule["_id"],
        )

    _send_reminder(rule, household_id)
    return "reminder_sent", None


def _auto_create_transaction(rule: dict, household_id: ObjectId) -> ObjectId:
    wallet = get_household_wallet(household_id, str(rule["wallet_id"]))
    now = datetime.now(timezone.utc)
    user_id = _attribution_user_id(household_id)

    doc = {
        "household_id": household_id,
        "wallet_id": wallet["_id"],
        "category_id": rule["category_id"],
        "user_id": user_id,
        "type": rule["type"],
        "amount": rule["amount"],
        "transfer_to_wallet_id": None,
        "merchant_name": rule.get("merchant_name"),
        "note": "Auto-created from recurring rule",
        "date": rule["next_due_date"],
        "source": "manual",
        "sms_id": None,
        "recurring_rule_id": rule["_id"],
        "created_at": now,
        "updated_at": now,
    }
    txn = create_single_wallet_transaction(household_id, wallet, doc)
    return txn["_id"]


def _send_reminder(rule: dict, household_id: ObjectId) -> None:
    payload = {
        "recurring_rule_id": str(rule["_id"]),
        "merchant_name": rule.get("merchant_name"),
        "amount": rule.get("amount"),
        "frequency": rule.get("frequency"),
    }
    title = "Recurring payment due"
    amount_text = f"₹{rule['amount']}" if rule.get("amount") is not None else "an amount"
    body = f"{rule.get('merchant_name')} ({amount_text}) is due — confirm or skip it."
    notify_household(household_id, "recurring_reminder", payload, title, body)

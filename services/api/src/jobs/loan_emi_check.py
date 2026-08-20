"""Loan EMI due-date job (LED-14), mirroring
jobs/recurring_transactions_check.py's shape closely — same "plain callable
function dispatched via EventBridge Scheduler" rationale (see that job's
module docstring / docs/decisions/0005-eventbridge-scheduler-for-jobs.md).

For every is_active=true loans doc whose next_due_date has arrived
(<= today):
  - Computes the interest/principal split of this payment against the
    loan's current outstanding_balance via shared.loans.compute_emi_split
    (standard reducing-balance EMI, clamped so the final payment never
    overshoots to a negative balance).
  - Creates an expense transaction via
    shared.transactions_engine.create_single_wallet_transaction against the
    loan's wallet_id/category_id (the single write path for anything
    touching a wallet's cached current_balance — never a raw insert/$inc
    here), dated to the loan's next_due_date, with source="manual" and
    loan_id set so payment history is queryable via
    GET /transactions?loan_id=....
  - Separately $inc's the loan doc's own outstanding_balance down by the
    principal_component (a different collection, so this doesn't need the
    multi-document Mongo transaction machinery create_single_wallet_transaction
    uses for wallets) and advances next_due_date by exactly one month via
    shared.recurring.advance_next_due_date, same helper
    recurring_rule_skip_next/jobs/recurring_transactions_check.py use, kept
    to "monthly" always since EMI schedules don't support other
    frequencies (see shared/loans.py's module docstring).
  - If this was the final payment (principal_component pays off the
    remaining balance exactly), the loan is also marked is_active=False so
    it stops appearing in future runs and future net-worth liability sums.

Transaction attribution: same as recurring_transactions_check — loans
doesn't record which household member created it, and user_id on a
transaction is attribution-only, so a job-created transaction is
attributed to an arbitrary household member (the first one returned).
"""
import logging
from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_loans_collection
from shared.loans import compute_emi_split
from shared.notify import get_household_members
from shared.recurring import advance_next_due_date
from shared.transactions_engine import create_single_wallet_transaction, get_household_wallet

logger = logging.getLogger(__name__)


def _attribution_user_id(household_id: ObjectId) -> ObjectId | None:
    members = get_household_members(household_id)
    return members[0]["_id"] if members else None


def run_loan_emi_check(today: "datetime | None" = None) -> list[dict]:
    """Returns a list of {loan_id, action, transaction_id} entries for every
    due loan processed in this run. action is always "emi_paid". next_due_date
    is stored as a naive datetime (matching models/loan_create's parsing of
    a date-only ISO string), so `today` is normalized to naive UTC here too
    — comparing a naive Mongo-stored value against an aware one raises in
    real pymongo."""
    today = (today or datetime.now(timezone.utc)).replace(tzinfo=None)
    processed = []

    query = {"is_active": True, "next_due_date": {"$lte": today}}
    for loan in get_loans_collection().find(query):
        household_id = loan["household_id"]
        loan_id = loan["_id"]

        try:
            transaction_id = _pay_emi(loan, household_id)
        except Exception:
            logger.exception("failed to process loan emi loan_id=%s", loan_id)
            continue

        processed.append({"loan_id": loan_id, "action": "emi_paid", "transaction_id": transaction_id})

    return processed


def _pay_emi(loan: dict, household_id: ObjectId) -> ObjectId:
    wallet = get_household_wallet(household_id, str(loan["wallet_id"]))
    split = compute_emi_split(loan["outstanding_balance"], loan["annual_interest_rate"], loan["emi_amount"])
    paid_amount = split.interest_component + split.principal_component

    now = datetime.now(timezone.utc)
    user_id = _attribution_user_id(household_id)

    doc = {
        "household_id": household_id,
        "wallet_id": wallet["_id"],
        "category_id": loan["category_id"],
        "user_id": user_id,
        "type": "expense",
        "amount": paid_amount,
        "transfer_to_wallet_id": None,
        "merchant_name": loan.get("name"),
        "note": "Auto-created EMI payment",
        "date": loan["next_due_date"],
        "source": "manual",
        "sms_id": None,
        "recurring_rule_id": None,
        "loan_id": loan["_id"],
        "created_at": now,
        "updated_at": now,
    }
    txn = create_single_wallet_transaction(household_id, wallet, doc)

    next_due_date = advance_next_due_date(loan["next_due_date"], "monthly")
    updates = {
        "next_due_date": datetime.combine(next_due_date, datetime.min.time()),
        "updated_at": now,
    }
    if split.is_final_payment:
        updates["is_active"] = False

    get_loans_collection().update_one(
        {"_id": loan["_id"]},
        {
            "$inc": {"outstanding_balance": -split.principal_component},
            "$set": updates,
        },
    )

    return txn["_id"]

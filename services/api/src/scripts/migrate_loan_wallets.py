"""One-off, idempotent migration for LED-14's move of loans out of the
wallets collection into their own dedicated `loans` collection.

For every wallet with type == "loan" that hasn't already been migrated:
  - Creates a new `loans` collection doc, preserving the wallet's
    current_balance as the loan's starting outstanding_balance (that's the
    live, correctly-drifted-and-corrected figure — not the original
    principal, which loan_details.principal may or may not still reflect
    accurately) and copying over whatever amortization fields loan_details
    holds (plan.md §4: `{principal, interest_rate, tenure_months,
    emi_amount, start_date}`).
  - Needs a wallet_id (the source wallet future EMI payments will debit
    from) and a category_id for the new loan doc, neither of which exists
    on the old loan wallet itself. Best-effort: picks the household's
    first non-archived bank_account wallet as the EMI source, and an
    expense category named "Loan Payment" if the household has one, else
    falls back to the household's first non-archived expense category.
    Logs a warning and SKIPS the wallet (leaving it unmigrated, safe to
    re-run) if neither can be found — those households need a manual
    wallet_id/category_id assignment before this script can finish for
    them, rather than guessing something wrong.
  - Sets the wallet's is_archived = True and migrated_to_loan_id = <new
    loan _id> (do NOT delete the wallet doc — its historical transactions
    must still resolve to it). migrated_to_loan_id is also the idempotency
    guard: a wallet with it already set is skipped on re-run.

next_due_date for the migrated loan is computed the same way
models/loan_create/compute.py does for a brand-new loan (one month after
start_date) when loan_details.start_date is present; when it's missing
(old data may not have had a start_date), next_due_date is set to today so
the loan is immediately eligible for jobs/loan_emi_check.py rather than
silently never coming due.

Usage (from services/api/src, with MONGO_URI/MONGO_DB_NAME configured):

    python -m scripts.migrate_loan_wallets

Not run against any live database as part of LED-14 — see that ticket.
"""
import logging
from datetime import datetime, timezone

from shared.db import get_categories_collection, get_loans_collection, get_wallets_collection
from shared.recurring import advance_due_date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOAN_PAYMENT_CATEGORY_NAME = "Loan Payment"


def _find_source_wallet(household_id):
    return get_wallets_collection().find_one(
        {"household_id": household_id, "type": "bank_account", "is_archived": {"$ne": True}}
    )


def _find_category(household_id):
    categories = get_categories_collection()
    category = categories.find_one(
        {"household_id": household_id, "name": LOAN_PAYMENT_CATEGORY_NAME, "type": "expense"}
    )
    if category:
        return category
    return categories.find_one({"household_id": household_id, "type": "expense", "is_archived": {"$ne": True}})


def _next_due_date(loan_details: dict, now: datetime) -> datetime:
    start_date_raw = (loan_details or {}).get("start_date")
    if start_date_raw:
        start_date = start_date_raw if isinstance(start_date_raw, datetime) else datetime.fromisoformat(start_date_raw)
        next_due = advance_due_date(start_date.date(), "monthly")
        return datetime.combine(next_due, datetime.min.time())
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def main() -> None:
    wallets = get_wallets_collection()
    loans = get_loans_collection()
    now = datetime.now(timezone.utc)

    query = {"type": "loan", "migrated_to_loan_id": {"$exists": False}}
    migrated_count = 0
    skipped_count = 0

    for wallet in wallets.find(query):
        household_id = wallet["household_id"]
        loan_details = wallet.get("loan_details") or {}

        source_wallet = _find_source_wallet(household_id)
        category = _find_category(household_id)
        if not source_wallet or not category:
            logger.warning(
                "wallet_id=%s (household_id=%s): could not find a %s to migrate to a loan doc — skipping, "
                "needs manual wallet_id/category_id assignment",
                wallet["_id"],
                household_id,
                "source bank_account wallet" if not source_wallet else "'Loan Payment' or expense category",
            )
            skipped_count += 1
            continue

        start_date_raw = loan_details.get("start_date")
        start_date = (
            start_date_raw
            if isinstance(start_date_raw, datetime)
            else (datetime.fromisoformat(start_date_raw) if start_date_raw else now)
        )

        loan_doc = {
            "household_id": household_id,
            "name": wallet.get("name") or "Migrated Loan",
            "wallet_id": source_wallet["_id"],
            "category_id": category["_id"],
            "principal": loan_details.get("principal"),
            "annual_interest_rate": loan_details.get("interest_rate"),
            "tenure_months": loan_details.get("tenure_months"),
            "emi_amount": loan_details.get("emi_amount"),
            "outstanding_balance": wallet.get("current_balance", 0) or 0,
            "start_date": start_date,
            "next_due_date": _next_due_date(loan_details, now),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        result = loans.insert_one(loan_doc)

        wallets.update_one(
            {"_id": wallet["_id"]},
            {"$set": {"is_archived": True, "migrated_to_loan_id": result.inserted_id, "updated_at": now}},
        )

        logger.info(
            "migrated wallet_id=%s -> loan_id=%s (household_id=%s, outstanding_balance=%s)",
            wallet["_id"],
            result.inserted_id,
            household_id,
            loan_doc["outstanding_balance"],
        )
        migrated_count += 1

    logger.info("migrate_loan_wallets: migrated=%d skipped=%d", migrated_count, skipped_count)


if __name__ == "__main__":
    main()

from datetime import datetime, timezone

from shared.db import get_loans_collection
from shared.output import ValidationError
from shared.recurring import advance_due_date
from shared.scope import get_household_category, require_household_id
from shared.transactions_engine import get_household_wallet


def create_loan(inp, user_id: str) -> dict:
    household_id = require_household_id(user_id)
    wallet = get_household_wallet(household_id, inp.wallet_id)
    category = get_household_category(household_id, inp.category_id)

    if category.get("is_archived"):
        raise ValidationError("category_is_archived")
    if category["type"] != "expense":
        raise ValidationError("category_type_mismatch")

    now = datetime.now(timezone.utc)
    # Stored naive (matching recurring_rule_create's parsing of a date-only
    # ISO string) so it compares cleanly against the naive `today` that
    # jobs/loan_emi_check.py queries with.
    start_date = datetime.fromisoformat(inp.start_date).replace(tzinfo=None)
    # First EMI falls due one month after the loan starts, same cycle math
    # jobs/loan_emi_check.py/skip-next-style flows use to advance afterward.
    next_due_date = advance_due_date(start_date.date(), "monthly")

    doc = {
        "household_id": household_id,
        "name": inp.name.strip(),
        "wallet_id": wallet["_id"],
        "category_id": category["_id"],
        "principal": inp.principal,
        "annual_interest_rate": inp.annual_interest_rate,
        "tenure_months": inp.tenure_months,
        "emi_amount": inp.emi_amount,
        "outstanding_balance": inp.principal,
        "start_date": start_date,
        "next_due_date": datetime.combine(next_due_date, datetime.min.time()),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = get_loans_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

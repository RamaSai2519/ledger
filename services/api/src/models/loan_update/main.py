from datetime import datetime, timezone

from models.loan_update import validate
from shared.db import get_loans_collection
from shared.interfaces import LoanUpdateInput as Input
from shared.output import ValidationError, success
from shared.scope import get_household_category, get_household_loan, require_household_id
from shared.serializers import serialize_loan
from shared.transactions_engine import get_household_wallet


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    loan = get_household_loan(household_id, inp.loan_id)
    updates = validate.validate(inp.body)

    if "wallet_id" in updates:
        wallet = get_household_wallet(household_id, updates["wallet_id"])
        updates["wallet_id"] = wallet["_id"]

    if "category_id" in updates:
        category = get_household_category(household_id, updates["category_id"])
        if category.get("is_archived"):
            raise ValidationError("category_is_archived")
        if category["type"] != "expense":
            raise ValidationError("category_type_mismatch")
        updates["category_id"] = category["_id"]

    updates["updated_at"] = datetime.now(timezone.utc)

    get_loans_collection().update_one({"_id": loan["_id"]}, {"$set": updates})
    loan.update(updates)
    return success(serialize_loan(loan))

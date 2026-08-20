from shared.db import get_loans_collection
from shared.interfaces import LoanDeleteInput as Input
from shared.output import success
from shared.scope import get_household_loan, require_household_id


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    loan = get_household_loan(household_id, inp.loan_id)

    # Transactions previously created from this loan's EMI job keep their
    # loan_id reference for audit/history — deleting the loan never
    # cascades to them, mirroring recurring_rule_delete's treatment of
    # recurring_rule_id on past transactions.
    get_loans_collection().delete_one({"_id": loan["_id"]})
    return success({"id": str(loan["_id"]), "deleted": True})

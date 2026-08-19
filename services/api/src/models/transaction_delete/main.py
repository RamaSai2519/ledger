from shared.interfaces import TransactionDeleteInput as Input
from shared.output import success
from shared.scope import get_household_transaction, require_household_id
from shared.transactions_engine import delete_transaction


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    txn = get_household_transaction(household_id, inp.transaction_id)

    delete_transaction(txn)
    return success({"id": str(txn["_id"]), "deleted": True})

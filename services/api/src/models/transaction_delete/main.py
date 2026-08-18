from shared.output import success
from shared.scope import get_household_transaction, require_household_id
from shared.transactions_engine import delete_transaction


def process(transaction_id: str, user_id: str):
    household_id = require_household_id(user_id)
    txn = get_household_transaction(household_id, transaction_id)

    delete_transaction(txn)
    return success({"id": str(txn["_id"]), "deleted": True})

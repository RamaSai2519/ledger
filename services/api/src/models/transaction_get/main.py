from shared.output import success
from shared.scope import get_household_transaction, require_household_id
from shared.serializers import serialize_transaction


def process(transaction_id: str, user_id: str):
    household_id = require_household_id(user_id)
    txn = get_household_transaction(household_id, transaction_id)
    return success(serialize_transaction(txn))

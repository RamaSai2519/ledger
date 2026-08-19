from shared.interfaces import TransactionGetInput as Input
from shared.output import success
from shared.scope import get_household_transaction, require_household_id
from shared.serializers import serialize_transaction


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    txn = get_household_transaction(household_id, inp.transaction_id)
    return success(serialize_transaction(txn))

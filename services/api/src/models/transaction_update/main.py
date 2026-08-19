from models.transaction_update import compute, validate
from shared.interfaces import TransactionUpdateInput as Input
from shared.output import success
from shared.scope import get_household_transaction, require_household_id
from shared.serializers import serialize_transaction


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    existing_txn = get_household_transaction(household_id, inp.transaction_id)
    updates = validate.validate(existing_txn, inp.body)

    updated = compute.update_transaction(household_id, existing_txn, updates)
    return success(serialize_transaction(updated))

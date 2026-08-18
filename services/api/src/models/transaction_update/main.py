from models.transaction_update import compute, validate
from shared.output import success
from shared.scope import get_household_transaction, require_household_id
from shared.serializers import serialize_transaction


def process(transaction_id: str, request_json: dict, user_id: str):
    household_id = require_household_id(user_id)
    existing_txn = get_household_transaction(household_id, transaction_id)
    updates = validate.validate(existing_txn, request_json)

    updated = compute.update_transaction(household_id, existing_txn, updates)
    return success(serialize_transaction(updated))

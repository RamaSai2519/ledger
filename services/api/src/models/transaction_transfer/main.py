from models.transaction_transfer import compute, validate
from shared.interfaces import TransactionTransferInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_transaction


def process(inp: Input):
    validate.validate(inp)

    household_id = require_household_id(inp.user_id)
    txn = compute.create_transfer(inp, inp.user_id, household_id)
    return success(serialize_transaction(txn))

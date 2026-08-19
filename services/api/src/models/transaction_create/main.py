from models.transaction_create import compute, validate
from shared.interfaces import TransactionCreateInput as Input
from shared.output import success
from shared.serializers import serialize_transaction


def process(inp: Input):
    validate.validate(inp)
    txn = compute.create_transaction(inp, inp.user_id)
    return success(serialize_transaction(txn))

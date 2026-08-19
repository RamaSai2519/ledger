from models.wallet_create import compute, validate
from shared.interfaces import WalletCreateInput as Input
from shared.output import success
from shared.serializers import serialize_wallet


def process(inp: Input):
    validate.validate(inp)
    wallet = compute.create_wallet(inp, inp.user_id)
    return success(serialize_wallet(wallet))

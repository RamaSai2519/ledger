from models.fcm_token_register import compute, validate
from shared.interfaces import FcmTokenRegisterInput as Input
from shared.output import success


def process(inp: Input):
    validate.validate(inp)
    compute.register_token(inp, inp.user_id)
    return success({"registered": True})


from models.pin_set import compute, validate
from shared.interfaces import PinSetInput as Input
from shared.output import success


def process(inp: Input):
    validate.validate(inp)
    compute.set_pin(inp, inp.user_id)
    return success({"pin_set": True})

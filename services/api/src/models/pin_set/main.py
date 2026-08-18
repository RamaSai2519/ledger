from dataclasses import dataclass

from models.pin_set import compute, validate
from shared.output import success


@dataclass
class Input:
    pin: str


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    compute.set_pin(inp, user_id)
    return success({"pin_set": True})

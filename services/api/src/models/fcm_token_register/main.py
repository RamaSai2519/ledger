from dataclasses import dataclass

from models.fcm_token_register import compute, validate
from shared.output import success


@dataclass
class Input:
    token: str


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    compute.register_token(inp, user_id)
    return success({"registered": True})

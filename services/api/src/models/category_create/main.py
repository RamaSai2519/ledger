from dataclasses import dataclass

from models.category_create import compute, validate
from shared.output import success
from shared.serializers import serialize_category


@dataclass
class Input:
    name: str
    type: str
    icon: str | None = None
    color: str | None = None


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    category = compute.create_category(inp, user_id)
    return success(serialize_category(category))

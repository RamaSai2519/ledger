from dataclasses import dataclass

from models.household_create import compute, validate
from shared.output import success


@dataclass
class Input:
    name: str = "My Household"


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    household = compute.create_household(inp, user_id)
    return success(
        {
            "household_id": str(household["_id"]),
            "name": household["name"],
            "invite_code": household["invite_code"],
        }
    )

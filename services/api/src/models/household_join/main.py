from dataclasses import dataclass

from models.household_join import compute, validate
from shared.output import success


@dataclass
class Input:
    invite_code: str


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    household = compute.join_household(inp, user_id)
    return success(
        {
            "household_id": str(household["_id"]),
            "name": household["name"],
            "member_count": len(household["member_ids"]),
        }
    )


from models.household_create import compute, validate
from shared.interfaces import HouseholdCreateInput as Input
from shared.output import success


def process(inp: Input):
    validate.validate(inp)
    household = compute.create_household(inp, inp.user_id)
    return success(
        {
            "household_id": str(household["_id"]),
            "name": household["name"],
            "invite_code": household["invite_code"],
        }
    )

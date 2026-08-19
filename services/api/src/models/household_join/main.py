
from models.household_join import compute, validate
from shared.interfaces import HouseholdJoinInput as Input
from shared.output import success


def process(inp: Input):
    validate.validate(inp)
    household = compute.join_household(inp, inp.user_id)
    return success(
        {
            "household_id": str(household["_id"]),
            "name": household["name"],
            "member_count": len(household["member_ids"]),
        }
    )

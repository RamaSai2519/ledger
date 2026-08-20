from models.household_preview import compute, validate
from shared.interfaces import HouseholdPreviewInput as Input
from shared.output import success


def process(inp: Input):
    validate.validate(inp)
    household = compute.preview_household(inp)
    return success(
        {
            "name": household["name"],
            "member_count": len(household["member_ids"]),
            "created_at": household["created_at"].isoformat(),
        }
    )

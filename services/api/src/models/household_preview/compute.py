from shared.db import get_households_collection
from shared.output import NotFoundError


def preview_household(inp) -> dict:
    household = get_households_collection().find_one({"invite_code": inp.invite_code.upper()})
    if not household:
        raise NotFoundError("invalid_invite_code")
    return household

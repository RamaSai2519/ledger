from models.household_members import compute
from shared.interfaces import HouseholdMembersInput as Input
from shared.output import success
from shared.serializers import serialize_user


def process(inp: Input):
    members = compute.list_members(inp.user_id)
    return success({"members": [serialize_user(member) for member in members]})

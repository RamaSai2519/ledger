from models.profile_update import compute, validate
from shared.interfaces import ProfileUpdateInput as Input
from shared.output import success
from shared.serializers import serialize_user


def process(inp: Input):
    updates = validate.validate(inp.body)
    user = compute.update_profile(inp.user_id, updates)
    return success(serialize_user(user))

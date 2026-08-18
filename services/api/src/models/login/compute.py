from datetime import datetime, timezone

from shared.auth_utils import is_locked_out, next_lockout_state, verify_password
from shared.db import get_users_collection
from shared.output import AuthError


def authenticate(inp) -> dict:
    users = get_users_collection()
    user = users.find_one({"mobile_number": inp.mobile_number})
    if not user:
        raise AuthError("invalid_credentials")

    if is_locked_out(user):
        raise AuthError("account_locked_try_later")

    ok = verify_password(inp.password, user["password_hash"])
    users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                **next_lockout_state(user, success=ok),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    if not ok:
        raise AuthError("invalid_credentials")

    return user

from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_users_collection
from shared.output import NotFoundError


def register_token(inp, user_id: str) -> None:
    users = get_users_collection()
    # $addToSet dedupes by string equality — no separate cleanup job needed
    # to keep fcm_tokens from growing unbounded on repeat logins from the
    # same device (a fresh FCM token per install/reinstall is expected, but
    # re-registering the *same* token, e.g. app relaunch, is a no-op here).
    result = users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$addToSet": {"fcm_tokens": inp.token.strip()},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    if result.matched_count == 0:
        raise NotFoundError("user_not_found")

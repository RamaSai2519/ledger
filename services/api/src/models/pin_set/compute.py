from datetime import datetime, timezone

from bson import ObjectId

from shared.auth_utils import hash_password
from shared.db import get_users_collection
from shared.output import NotFoundError


def set_pin(inp, user_id: str) -> None:
    users = get_users_collection()
    result = users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"pin_hash": hash_password(inp.pin), "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise NotFoundError("user_not_found")

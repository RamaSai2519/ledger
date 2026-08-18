from datetime import datetime, timezone

from shared.auth_utils import hash_password
from shared.db import get_users_collection
from shared.output import ConflictError


def create_user(inp) -> dict:
    users = get_users_collection()
    if users.find_one({"mobile_number": inp.mobile_number}):
        raise ConflictError("mobile_number_already_registered")

    now = datetime.now(timezone.utc)
    doc = {
        "mobile_number": inp.mobile_number,
        "password_hash": hash_password(inp.password),
        "name": inp.name.strip(),
        "household_id": None,
        "pin_hash": None,
        "fcm_tokens": [],
        "failed_login_attempts": 0,
        "locked_until": None,
        "created_at": now,
        "updated_at": now,
    }
    result = users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

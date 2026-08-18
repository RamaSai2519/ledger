import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from shared.constants import INVITE_CODE_ALPHABET, INVITE_CODE_LENGTH
from shared.configs import CONFIG


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_invite_code() -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


def _as_aware_utc(value: datetime) -> datetime:
    # pymongo (and mongomock) round-trip datetimes as naive UTC by default —
    # tag them back as UTC-aware instead of comparing naive vs. aware, which
    # raises TypeError.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def is_locked_out(user: dict) -> bool:
    locked_until = user.get("locked_until")
    return bool(locked_until and _as_aware_utc(locked_until) > datetime.now(timezone.utc))


def next_lockout_state(user: dict, success: bool) -> dict:
    """Returns the fields to $set on the user doc after a login attempt."""
    if success:
        return {"failed_login_attempts": 0, "locked_until": None}

    attempts = user.get("failed_login_attempts", 0) + 1
    update = {"failed_login_attempts": attempts}
    if attempts >= CONFIG["login_max_attempts"]:
        update["locked_until"] = datetime.now(timezone.utc) + timedelta(
            minutes=CONFIG["login_lockout_minutes"]
        )
    return update

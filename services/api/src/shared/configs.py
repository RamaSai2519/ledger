import json
import os


def _get_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


def _load_firebase_credentials() -> str:
    """Load Firebase credentials from file path or inline JSON.

    Supports two env vars (checked in order):
    1. FIREBASE_CREDENTIALS_FILE — path to a service-account JSON file
    2. FIREBASE_CREDENTIALS_JSON — inline JSON string (legacy, breaks with
       multiline private keys in .env files)
    """
    file_path = os.environ.get("FIREBASE_CREDENTIALS_FILE", "")
    if file_path and os.path.isfile(file_path):
        with open(file_path) as f:
            return json.dumps(json.load(f))  # normalize to single-line JSON

    return os.environ.get("FIREBASE_CREDENTIALS_JSON", "")


CONFIG = {
    "env": os.environ.get("ENV", "dev"),
    "mongo_uri": os.environ.get("MONGO_URI", ""),
    "mongo_db_name": os.environ.get("MONGO_DB_NAME", "ledger"),
    "jwt_secret_key": os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me"),
    "access_token_minutes": int(os.environ.get("ACCESS_TOKEN_MINUTES", "15")),
    "refresh_token_days": int(os.environ.get("REFRESH_TOKEN_DAYS", "30")),
    "login_max_attempts": int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5")),
    "login_lockout_minutes": int(os.environ.get("LOGIN_LOCKOUT_MINUTES", "15")),
    "debug": _get_bool("DEBUG", False),
    "firebase_credentials_json": _load_firebase_credentials(),
    "bill_due_reminder_days": int(os.environ.get("BILL_DUE_REMINDER_DAYS", "3")),
}

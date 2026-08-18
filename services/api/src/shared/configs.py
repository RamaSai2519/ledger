import os


def _get_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


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
}

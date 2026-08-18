from datetime import datetime, timezone

from shared.db import get_revoked_tokens_collection
from shared.output import success


def process(jti: str, expires_at: datetime):
    get_revoked_tokens_collection().insert_one(
        {
            "jti": jti,
            "expires_at": expires_at,
            "revoked_at": datetime.now(timezone.utc),
        }
    )
    return success({"logged_out": True})

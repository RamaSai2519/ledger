from datetime import datetime, timezone

from shared.db import get_revoked_tokens_collection
from shared.interfaces import LogoutInput as Input
from shared.output import success


def process(inp: Input):
    get_revoked_tokens_collection().insert_one(
        {
            "jti": inp.jti,
            "expires_at": inp.expires_at,
            "revoked_at": datetime.now(timezone.utc),
        }
    )
    return success({"logged_out": True})

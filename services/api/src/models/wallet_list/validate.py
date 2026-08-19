from shared.balance import WALLET_TYPES
from shared.output import ValidationError


def validate(query) -> None:
    if query.include_archived is not None and query.include_archived.lower() not in ("true", "false"):
        raise ValidationError(f"invalid_include_archived: {query.include_archived}")
    if query.type is not None and query.type not in WALLET_TYPES:
        raise ValidationError(f"invalid_wallet_type: {query.type}")

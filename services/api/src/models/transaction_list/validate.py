from datetime import datetime

from shared.balance import TRANSACTION_TYPES
from shared.output import ValidationError


def _validate_date(value: str | None, field: str) -> None:
    if not value:
        return
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"invalid_{field}: {value}") from exc


def validate(query) -> None:
    if query.type is not None and query.type not in TRANSACTION_TYPES:
        raise ValidationError(f"invalid_transaction_type: {query.type}")
    _validate_date(query.from_, "from")
    _validate_date(query.to, "to")

from datetime import datetime

from shared.output import ValidationError


def _validate_date(value: str | None, field: str) -> None:
    if not value:
        return
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"invalid_{field}: {value}") from exc


def validate(query) -> None:
    _validate_date(query.from_, "from")
    _validate_date(query.to, "to")

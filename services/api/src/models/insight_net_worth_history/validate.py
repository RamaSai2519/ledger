from datetime import datetime, timezone

from shared.output import ValidationError


def validate(from_str: str | None, to_str: str | None) -> tuple[datetime | None, datetime | None]:
    def parse(value):
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError(f"invalid_date: {value}") from exc
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    from_date, to_date = parse(from_str), parse(to_str)
    if from_date and to_date and from_date > to_date:
        raise ValidationError("from_must_be_before_to")
    return from_date, to_date

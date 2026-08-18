from shared.insights import validate_period


def validate(period: str | None) -> str:
    return validate_period(period)

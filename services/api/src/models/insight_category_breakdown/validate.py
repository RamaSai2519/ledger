from shared.insights import validate_period


def validate(query) -> str:
    return validate_period(query.period)

import re

from shared.output import ValidationError

PIN_RE = re.compile(r"^\d{4,6}$")


def validate(inp) -> None:
    if not PIN_RE.match(inp.pin):
        raise ValidationError("pin_must_be_4_to_6_digits")

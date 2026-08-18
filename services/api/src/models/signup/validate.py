import re

from shared.output import ValidationError

# Indian mobile numbers only — the product is INR-only per IMPLEMENTATION_PLAN.md.
MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def validate(inp) -> None:
    if not MOBILE_RE.match(inp.mobile_number):
        raise ValidationError("invalid_mobile_number")
    if len(inp.password) < 8:
        raise ValidationError("password_too_short")
    if not inp.name.strip():
        raise ValidationError("name_required")

from shared.constants import INVITE_CODE_LENGTH
from shared.output import ValidationError


def validate(inp) -> None:
    if not inp.invite_code or len(inp.invite_code) != INVITE_CODE_LENGTH:
        raise ValidationError("invalid_invite_code_format")

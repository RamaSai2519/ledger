from dataclasses import asdict, dataclass, is_dataclass
from typing import Any


@dataclass
class Output:
    status: str  # "SUCCESS" | "FAILURE"
    data: Any = None
    error: str | None = None


def success(data: Any = None) -> tuple[dict, int]:
    if is_dataclass(data):
        data = asdict(data)
    return asdict(Output(status="SUCCESS", data=data)), 200


def failure(error: str, code: int = 400) -> tuple[dict, int]:
    return asdict(Output(status="FAILURE", error=error)), code


class ValidationError(Exception):
    """Raised by a model's validate.py on bad input. Caught centrally in main.py."""


class NotFoundError(Exception):
    """Raised when a referenced document doesn't exist."""


class ConflictError(Exception):
    """Raised on a uniqueness / state conflict (e.g. duplicate mobile number)."""


class AuthError(Exception):
    """Raised on bad credentials / lockout."""

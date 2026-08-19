"""Shared page/page_size parsing for list endpoints, so every paginated
route validates and defaults pagination the same way instead of each
reimplementing (and subtly diverging on) the same int-parsing logic.
"""
from typing import Protocol

from shared.output import ValidationError

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class PaginationQuery(Protocol):
    page: str | None
    page_size: str | None


def parse_pagination(query: PaginationQuery) -> tuple[int, int]:
    try:
        page = max(1, int(query.page)) if query.page else 1
        page_size = min(MAX_PAGE_SIZE, max(1, int(query.page_size))) if query.page_size else DEFAULT_PAGE_SIZE
    except ValueError as exc:
        raise ValidationError("invalid_pagination_params") from exc
    return page, page_size

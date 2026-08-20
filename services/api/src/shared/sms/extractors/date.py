"""DateExtractor — spec Part 11.

Parses the date formats banks actually use; falls back to the SMS received
time (marked `inferred=True`) when the body has no explicit date.
"""
from __future__ import annotations

import re
from datetime import datetime

from shared.sms.types import FieldValue

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_NUMERIC_DATE = re.compile(r"\b(?P<d>\d{1,2})[-/](?P<m>\d{1,2})[-/](?P<y>\d{2}|\d{4})\b")
_TEXT_MONTH_DATE = re.compile(
    r"\b(?P<d>\d{1,2})[- ](?P<mon>[A-Za-z]{3})[a-z]*[- ](?P<y>\d{2}|\d{4})\b", re.IGNORECASE
)


def _resolve_year(y: str) -> int:
    year = int(y)
    if year < 100:
        year += 2000
    return year


class DateExtractor:
    def extract(self, raw_text: str, received_at: datetime) -> FieldValue:
        match = _TEXT_MONTH_DATE.search(raw_text)
        if match:
            month = _MONTHS.get(match.group("mon").lower())
            if month:
                try:
                    dt = datetime(_resolve_year(match.group("y")), month, int(match.group("d")))
                    return FieldValue(value=dt, confidence=0.9, evidence=["matched explicit D-Mon-YY date in message"])
                except ValueError:
                    pass

        match = _NUMERIC_DATE.search(raw_text)
        if match:
            try:
                dt = datetime(_resolve_year(match.group("y")), int(match.group("m")), int(match.group("d")))
                return FieldValue(value=dt, confidence=0.85, evidence=["matched explicit DD-MM-YY date in message"])
            except ValueError:
                pass

        return FieldValue(
            value=received_at,
            confidence=0.5,
            evidence=["no explicit date in message body - inferred from SMS received time"],
        )

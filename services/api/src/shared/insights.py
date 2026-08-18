"""Period bucketing shared by the /insights/* endpoints (plan.md §9).

`trends`, `income-vs-expense`, and `category-breakdown` all accept the same
`period=daily|monthly|yearly` query param and the same `from`/`to` override
semantics, so the range-resolution and day/month/year bucketing logic lives
here once rather than being reimplemented per endpoint.
"""
from calendar import monthrange
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from shared.db import get_transactions_collection
from shared.output import ValidationError

PERIODS = {"daily", "monthly", "yearly"}

# Defaults per plan.md/LED-6 spec: "sensible defaults if from/to omitted
# (e.g. last 30 days for daily, last 12 months for monthly, last 5 years
# for yearly)".
_DEFAULT_DAYS = 30
_DEFAULT_MONTHS = 12
_DEFAULT_YEARS = 5


def validate_period(period: str | None) -> str:
    period = period or "daily"
    if period not in PERIODS:
        raise ValidationError(f"invalid_period: {period}")
    return period


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"invalid_date: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def resolve_range(period: str, from_str: str | None, to_str: str | None, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Returns (start, end) inclusive datetime bounds for the query. Falls
    back to the period-appropriate default window when either bound is
    omitted, per LED-6's spec."""
    now = now or datetime.now(timezone.utc)
    to_date = _parse_date(to_str)
    if to_date is None:
        to_date = _end_of_day(now)
    elif "T" not in to_str:
        # A bare "YYYY-MM-DD" `to` bound means "through the end of that
        # day," not midnight at its start — otherwise every transaction
        # dated later that same day would be excluded from the range.
        to_date = _end_of_day(to_date)

    from_date = _parse_date(from_str)
    if from_date is None:
        if period == "daily":
            from_date = _start_of_day(to_date - timedelta(days=_DEFAULT_DAYS - 1))
        elif period == "monthly":
            year, month = to_date.year, to_date.month
            for _ in range(_DEFAULT_MONTHS - 1):
                month -= 1
                if month == 0:
                    month = 12
                    year -= 1
            from_date = datetime(year, month, 1, tzinfo=timezone.utc)
        else:  # yearly
            from_date = datetime(to_date.year - (_DEFAULT_YEARS - 1), 1, 1, tzinfo=timezone.utc)

    if from_date > to_date:
        raise ValidationError("from_must_be_before_to")

    return from_date, to_date


def bucket_key(period: str, dt: datetime) -> str:
    if period == "daily":
        return dt.strftime("%Y-%m-%d")
    if period == "monthly":
        return dt.strftime("%Y-%m")
    return dt.strftime("%Y")


def generate_buckets(period: str, start: datetime, end: datetime) -> list[str]:
    """Ordered list of every bucket key in [start, end] so zero-activity
    buckets still render (a chart with gaps is worse than one with real
    zeros)."""
    buckets = []
    if period == "daily":
        cur = _start_of_day(start)
        last = _start_of_day(end)
        while cur <= last:
            buckets.append(bucket_key(period, cur))
            cur += timedelta(days=1)
    elif period == "monthly":
        year, month = start.year, start.month
        end_year, end_month = end.year, end.month
        while (year, month) <= (end_year, end_month):
            buckets.append(f"{year:04d}-{month:02d}")
            month += 1
            if month == 13:
                month = 1
                year += 1
    else:  # yearly
        for year in range(start.year, end.year + 1):
            buckets.append(str(year))
    return buckets


def month_end(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def aggregate_income_and_expense_by_bucket(
    household_id: ObjectId, period: str, start: datetime, end: datetime
) -> dict[str, dict[str, float]]:
    """Sums `expense` and `income` transactions household-wide into
    {bucket_key: {"expense": total, "income": total}}, seeded with zeros for
    every bucket in range so a chart never has to guess at gaps."""
    totals = {key: {"expense": 0.0, "income": 0.0} for key in generate_buckets(period, start, end)}

    query = {
        "household_id": household_id,
        "type": {"$in": ["expense", "income"]},
        "date": {"$gte": start, "$lte": end},
    }
    for txn in get_transactions_collection().find(query):
        date = txn.get("date")
        if not date:
            continue
        key = bucket_key(period, date)
        bucket = totals.setdefault(key, {"expense": 0.0, "income": 0.0})
        bucket[txn["type"]] += txn.get("amount", 0)

    return totals


def aggregate_expense_by_category(household_id: ObjectId, start: datetime, end: datetime) -> dict[ObjectId, float]:
    """Sums `expense` transactions grouped by category_id over [start, end]."""
    totals: dict[ObjectId, float] = {}
    query = {"household_id": household_id, "type": "expense", "date": {"$gte": start, "$lte": end}}
    for txn in get_transactions_collection().find(query):
        category_id = txn.get("category_id")
        if category_id is None:
            continue
        totals[category_id] = totals.get(category_id, 0.0) + txn.get("amount", 0)
    return totals

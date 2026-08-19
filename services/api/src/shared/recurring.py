"""Shared cycle-advance math for recurring_rules (plan.md §4/§10, LED-8).

Both models/recurring_rule_skip_next and jobs/recurring_transactions_check
need to advance a rule's next_due_date by exactly one cycle, and they must
never drift apart (same rationale as jobs/budget_threshold_check.py reusing
shared.budgets.compute_budget_progress instead of reimplementing it) — so
the math lives here once and both call sites import it.
"""
from calendar import monthrange
from datetime import date, datetime, timedelta

RECURRING_FREQUENCIES = {"weekly", "monthly", "yearly"}


def _clamp_day(year: int, month: int, day: int) -> int:
    last_day = monthrange(year, month)[1]
    return min(day, last_day)


def advance_due_date(current: date, frequency: str) -> date:
    """Returns the next occurrence of current after one cycle of frequency.
    weekly = +7 days. monthly = same day next month, clamped to the target
    month's last valid day (e.g. Jan 31 -> Feb 28/29). yearly = same
    month/day next year, clamped for Feb 29 -> non-leap year (-> Feb 28)."""
    if frequency == "weekly":
        return current + timedelta(days=7)

    if frequency == "monthly":
        year = current.year
        month = current.month + 1
        if month > 12:
            year += 1
            month = 1
        day = _clamp_day(year, month, current.day)
        return date(year, month, day)

    if frequency == "yearly":
        year = current.year + 1
        day = _clamp_day(year, current.month, current.day)
        return date(year, current.month, day)

    raise ValueError(f"invalid_recurring_frequency: {frequency}")


def advance_next_due_date(current: "date | datetime", frequency: str) -> date:
    """Same as advance_due_date but tolerates a datetime (as stored in Mongo)
    by normalizing to a plain date first."""
    if isinstance(current, datetime):
        current = current.date()
    return advance_due_date(current, frequency)

from bson import ObjectId

from shared.insights import aggregate_income_and_expense_by_bucket, generate_buckets, resolve_range


def get_income_vs_expense(household_id: ObjectId, period: str, from_str: str | None, to_str: str | None) -> dict:
    """Income and expense totals side by side per bucket (plan.md §9's
    income-vs-expense comparison view). Shares the same bucketing helper as
    insight_trends so the two endpoints never disagree on a given bucket's
    totals — this endpoint's contract is the paired shape, not a different
    computation."""
    start, end = resolve_range(period, from_str, to_str)
    totals = aggregate_income_and_expense_by_bucket(household_id, period, start, end)

    points = []
    for key in generate_buckets(period, start, end):
        income = totals[key]["income"]
        expense = totals[key]["expense"]
        points.append({"bucket": key, "income": income, "expense": expense, "net": income - expense})

    return {
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "points": points,
    }

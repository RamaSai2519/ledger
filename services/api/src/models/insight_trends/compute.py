from bson import ObjectId

from shared.insights import aggregate_income_and_expense_by_bucket, generate_buckets, resolve_range


def get_trends(household_id: ObjectId, period: str, from_str: str | None, to_str: str | None) -> dict:
    """Total expense (and income, for context) aggregated by day/month/year
    bucket over the requested range (plan.md §9's trend chart)."""
    start, end = resolve_range(period, from_str, to_str)
    totals = aggregate_income_and_expense_by_bucket(household_id, period, start, end)

    points = [
        {"bucket": key, "expense": totals[key]["expense"], "income": totals[key]["income"]}
        for key in generate_buckets(period, start, end)
    ]

    return {
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "points": points,
    }

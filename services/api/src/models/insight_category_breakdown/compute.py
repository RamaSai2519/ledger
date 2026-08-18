from bson import ObjectId

from shared.db import get_categories_collection
from shared.insights import aggregate_expense_by_category, resolve_range


def get_category_breakdown(household_id: ObjectId, period: str, from_str: str | None, to_str: str | None) -> dict:
    """Sum of expense transactions grouped by category_id for the requested
    period (plan.md §9's category breakdown view), with category name/color
    denormalized in, sorted descending by amount."""
    start, end = resolve_range(period, from_str, to_str)
    totals = aggregate_expense_by_category(household_id, start, end)

    categories_by_id = {
        c["_id"]: c for c in get_categories_collection().find({"_id": {"$in": list(totals.keys())}})
    }

    items = []
    for category_id, amount in totals.items():
        category = categories_by_id.get(category_id)
        items.append(
            {
                "category_id": str(category_id),
                "category_name": category["name"] if category else "Unknown",
                "category_color": category.get("color") if category else None,
                "category_icon": category.get("icon") if category else None,
                "amount": amount,
            }
        )
    items.sort(key=lambda item: item["amount"], reverse=True)

    return {
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "items": items,
    }

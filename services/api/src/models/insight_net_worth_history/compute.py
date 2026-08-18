from datetime import datetime, timedelta, timezone

from bson import ObjectId

from shared.db import get_net_worth_snapshots_collection

# Default window when from/to are omitted, matching the "last N" defaults
# used by the other insights endpoints (shared/insights.py) — net worth is
# a monthly-cadence chart, so default to roughly a year back.
_DEFAULT_DAYS = 365


def _serialize(snapshot: dict) -> dict:
    return {
        "date": snapshot["date"].isoformat() if snapshot.get("date") else None,
        "total_assets": snapshot.get("total_assets", 0),
        "total_liabilities": snapshot.get("total_liabilities", 0),
        "net_worth": snapshot.get("net_worth", 0),
        "per_wallet_breakdown": {
            str(k): v for k, v in (snapshot.get("per_wallet_breakdown") or {}).items()
        },
    }


def get_net_worth_history(household_id: ObjectId, from_date: datetime | None, to_date: datetime | None) -> dict:
    """Reads precomputed daily snapshots from net_worth_snapshots (plan.md
    §4/§9) rather than replaying transaction history on the fly."""
    now = datetime.now(timezone.utc)
    to_date = to_date or now
    from_date = from_date or (to_date - timedelta(days=_DEFAULT_DAYS))

    query = {"household_id": household_id, "date": {"$gte": from_date, "$lte": to_date}}
    snapshots = list(get_net_worth_snapshots_collection().find(query).sort("date", 1))

    return {
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "snapshots": [_serialize(s) for s in snapshots],
    }

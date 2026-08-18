"""Nightly net-worth snapshot job (plan.md §4 net_worth_snapshots, §9, LED-6).

See jobs/budget_threshold_check.py's module docstring for why this is a
plain callable function dispatched via EventBridge Scheduler rather than
APScheduler (docs/decisions/0005-eventbridge-scheduler-for-jobs.md).

For every household, sums current_balance across bank_account/cash wallets
(assets) and credit_card/pay_later/loan wallets (liabilities), and upserts
one net_worth_snapshots doc per household per calendar day — keyed on
(household_id, date) so re-running the job the same day is idempotent
rather than creating duplicate snapshots.

Historical net worth is intentionally NOT computed on the fly (plan.md is
explicit: that requires replaying all transactions up to a date, which
doesn't scale for chart rendering) — this snapshot is the only way
net-worth-history data ever gets written.
"""
import logging
from datetime import datetime, timezone

from shared.balance import LIABILITY_WALLET_TYPES, ASSET_WALLET_TYPES
from shared.db import get_households_collection, get_net_worth_snapshots_collection, get_wallets_collection

logger = logging.getLogger(__name__)


def _today_midnight_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _compute_household_snapshot(household_id, as_of: datetime) -> dict:
    total_assets = 0.0
    total_liabilities = 0.0
    per_wallet_breakdown: dict[str, float] = {}

    wallets = get_wallets_collection().find({"household_id": household_id, "is_archived": {"$ne": True}})
    for wallet in wallets:
        balance = wallet.get("current_balance", 0) or 0
        wallet_type = wallet.get("type")
        per_wallet_breakdown[str(wallet["_id"])] = balance
        if wallet_type in ASSET_WALLET_TYPES:
            total_assets += balance
        elif wallet_type in LIABILITY_WALLET_TYPES:
            total_liabilities += balance

    return {
        "household_id": household_id,
        "date": as_of,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": total_assets - total_liabilities,
        "per_wallet_breakdown": per_wallet_breakdown,
    }


def run_net_worth_snapshot(now: datetime | None = None) -> list[dict]:
    """Returns a list of the snapshot doc upserted for each household."""
    as_of = _today_midnight_utc(now)
    snapshots_collection = get_net_worth_snapshots_collection()
    results = []

    for household in get_households_collection().find({}):
        household_id = household["_id"]
        try:
            snapshot = _compute_household_snapshot(household_id, as_of)
        except Exception:
            logger.exception("failed to compute net worth snapshot for household_id=%s", household_id)
            continue

        snapshots_collection.update_one(
            {"household_id": household_id, "date": as_of},
            {"$set": snapshot},
            upsert=True,
        )
        results.append(snapshot)

    return results

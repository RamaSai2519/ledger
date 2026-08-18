from datetime import datetime

from bson import ObjectId

from shared.balance import compute_delta
from shared.db import get_transactions_collection


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def get_balance_history(wallet: dict, from_date: str | None, to_date: str | None) -> list[dict]:
    """Reconstructs a running-balance series for the wallet from its
    opening_balance plus every transaction that touched it, in date order.
    Net-worth-over-time gets a real daily-snapshot job in a later phase
    (plan.md §4 net_worth_snapshots) — this is the simpler per-wallet
    on-the-fly version that's enough for a wallet detail screen sparkline.
    """
    transactions = get_transactions_collection()
    date_filter = {}
    lo, hi = _parse_date(from_date), _parse_date(to_date)
    if lo:
        date_filter["$gte"] = lo
    if hi:
        date_filter["$lte"] = hi

    base_query = {"$or": [{"wallet_id": wallet["_id"]}, {"transfer_to_wallet_id": wallet["_id"]}]}
    if date_filter:
        base_query["date"] = date_filter

    txns = list(transactions.find(base_query).sort("date", 1))

    running = wallet.get("opening_balance", 0)
    points = [{"date": None, "balance": running, "label": "opening_balance"}]
    for txn in txns:
        role = "source" if txn.get("wallet_id") == wallet["_id"] else "destination"
        txn_type = txn["type"] if txn["type"] != "transfer" else "transfer"
        delta = compute_delta(wallet["type"], txn_type, txn["amount"], role=role)
        running += delta
        points.append(
            {
                "date": txn["date"].isoformat() if txn.get("date") else None,
                "balance": running,
                "transaction_id": str(txn["_id"]),
                "label": txn["type"],
            }
        )
    return points

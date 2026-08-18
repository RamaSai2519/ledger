"""Nightly reconciliation safety net (plan.md §6): recomputes every wallet's
balance from opening_balance + full transaction history, and logs any
wallet whose cached current_balance has drifted from the recomputed value.

Not wired to a scheduler yet — APScheduler wiring is LED-5 (Budgets &
Notifications phase, plan.md §3/§15). This module is a plain importable
function so it can be called directly (and unit-tested directly) now, and
registered with APScheduler later without changing its signature.
"""
import logging

from bson import ObjectId

from shared.balance import compute_delta
from shared.db import get_transactions_collection, get_wallets_collection

logger = logging.getLogger(__name__)

DRIFT_EPSILON = 1e-6


def recompute_wallet_balance(wallet: dict) -> float:
    transactions = get_transactions_collection()
    total = wallet.get("opening_balance", 0)

    for txn in transactions.find({"wallet_id": wallet["_id"]}):
        role = "source" if txn["type"] == "transfer" else "primary"
        total += compute_delta(wallet["type"], txn["type"], txn["amount"], role=role)

    for txn in transactions.find({"transfer_to_wallet_id": wallet["_id"], "type": "transfer"}):
        total += compute_delta(wallet["type"], "transfer", txn["amount"], role="destination")

    return total


def reconcile_all_wallets(household_id: ObjectId | None = None) -> list[dict]:
    """Returns a list of {wallet_id, cached, recomputed} for every wallet
    whose cached current_balance has drifted from the recomputed value,
    logging a warning for each. Does not write anything — it's a detection
    pass, not an auto-correction (per CLAUDE.md: never silently overwrite a
    balance)."""
    query = {} if household_id is None else {"household_id": household_id}
    drifted = []

    for wallet in get_wallets_collection().find(query):
        recomputed = recompute_wallet_balance(wallet)
        cached = wallet.get("current_balance", 0)
        if abs(recomputed - cached) > DRIFT_EPSILON:
            logger.warning(
                "balance drift detected: wallet_id=%s name=%r cached=%s recomputed=%s",
                wallet["_id"],
                wallet.get("name"),
                cached,
                recomputed,
            )
            drifted.append({"wallet_id": wallet["_id"], "cached": cached, "recomputed": recomputed})

    return drifted

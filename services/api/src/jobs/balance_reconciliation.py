"""Nightly reconciliation safety net (plan.md §6): recomputes every wallet's
balance from opening_balance + full transaction history, logs any wallet
whose cached current_balance has drifted from the recomputed value, and
notifies the affected household(s) so a human can decide whether to
manually reconcile via POST /wallets/:id/reconcile. This job never
auto-corrects a balance — detection only (see CLAUDE.md).

Dispatched by index.py's scheduled_handler via EventBridge Scheduler
(infra/terraform/scheduler.tf) — see
docs/decisions/0005-eventbridge-scheduler-for-jobs.md for why jobs are
wired this way instead of APScheduler/Celery.
"""
import logging
from collections import defaultdict

from bson import ObjectId

from shared.balance import compute_delta
from shared.db import get_transactions_collection, get_wallets_collection
from shared.notify import notify_household

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
            drifted.append(
                {
                    "wallet_id": wallet["_id"],
                    "household_id": wallet["household_id"],
                    "wallet_name": wallet.get("name"),
                    "cached": cached,
                    "recomputed": recomputed,
                }
            )

    return drifted


def run_balance_reconciliation() -> list[dict]:
    """Runs reconcile_all_wallets() across every household, then fires one
    `balance_drift` notification per household with at least one drifted
    wallet (no notification when nothing has drifted, to avoid noise).
    Returns the flat list of drifted-wallet dicts from reconcile_all_wallets."""
    drifted = reconcile_all_wallets()

    by_household: dict[ObjectId, list[dict]] = defaultdict(list)
    for entry in drifted:
        by_household[entry["household_id"]].append(entry)

    for household_id, entries in by_household.items():
        payload = {
            "wallets": [
                {"wallet_id": str(e["wallet_id"]), "wallet_name": e["wallet_name"], "drift": e["recomputed"] - e["cached"]}
                for e in entries
            ]
        }
        if len(entries) == 1:
            title = "Balance drift detected"
            body = f"{entries[0]['wallet_name']} may be out of sync — please review and reconcile."
        else:
            title = "Balance drift detected"
            body = f"{len(entries)} wallets may be out of sync — please review and reconcile."

        notify_household(household_id, "balance_drift", payload, title, body)

    return drifted

"""The single write path for every transaction that touches a wallet's
cached current_balance. All of transaction_create, transaction_update,
transaction_delete, transaction_transfer, and wallet_reconcile route through
here so the $inc-and-insert (or $inc-and-delete) pairing can never drift
apart, and so multi-wallet writes (transfers) get the same session/fallback
transaction handling in one place.

mongomock (used in tests) doesn't support sessions/transactions at all
(raises NotImplementedError from start_session()), and even a real
standalone (non-replica-set) MongoDB rejects multi-document transactions.
`_run_atomically` tries a real session-backed transaction first and falls
back to sequential writes otherwise — correct either way for a single
process, just without the cross-document atomicity guarantee when the
underlying deployment can't provide it.
"""
from datetime import datetime, timezone

import pymongo
from bson import ObjectId

from shared.balance import compute_delta, reverse_delta
from shared.db import get_client, get_transactions_collection, get_wallets_collection
from shared.output import NotFoundError, ValidationError


def _run_atomically(fn) -> None:
    """Runs fn(session) inside a Mongo transaction when supported, else
    runs fn(None) as plain sequential writes."""
    client = get_client()
    try:
        with client.start_session() as session:
            with session.start_transaction():
                fn(session)
            return
    except (NotImplementedError, pymongo.errors.PyMongoError):
        pass
    fn(None)


def get_household_wallet(household_id: ObjectId, wallet_id: str) -> dict:
    try:
        oid = ObjectId(wallet_id)
    except Exception as exc:
        raise ValidationError("invalid_wallet_id") from exc
    wallet = get_wallets_collection().find_one({"_id": oid, "household_id": household_id})
    if not wallet:
        raise NotFoundError("wallet_not_found")
    return wallet


def create_single_wallet_transaction(household_id: ObjectId, wallet: dict, doc: dict) -> dict:
    """doc must already have type/amount/wallet_id/category_id/user_id/date/
    source/created_at/updated_at set; type is expense/income/adjustment."""
    transactions = get_transactions_collection()
    wallets = get_wallets_collection()
    delta = compute_delta(wallet["type"], doc["type"], doc["amount"])

    def _do(session):
        result = transactions.insert_one(dict(doc), session=session)
        wallets.update_one({"_id": wallet["_id"]}, {"$inc": {"current_balance": delta}}, session=session)
        doc["_id"] = result.inserted_id

    _run_atomically(_do)
    return doc


def create_transfer_transaction(household_id: ObjectId, source_wallet: dict, dest_wallet: dict, doc: dict) -> dict:
    """doc must have amount/user_id/date/source/created_at/updated_at set;
    type/wallet_id/transfer_to_wallet_id/category_id are set here."""
    transactions = get_transactions_collection()
    wallets = get_wallets_collection()

    doc = dict(doc)
    doc["type"] = "transfer"
    doc["wallet_id"] = source_wallet["_id"]
    doc["transfer_to_wallet_id"] = dest_wallet["_id"]
    doc["category_id"] = None

    source_delta = compute_delta(source_wallet["type"], "transfer", doc["amount"], role="source")
    dest_delta = compute_delta(dest_wallet["type"], "transfer", doc["amount"], role="destination")

    def _do(session):
        result = transactions.insert_one(dict(doc), session=session)
        wallets.update_one({"_id": source_wallet["_id"]}, {"$inc": {"current_balance": source_delta}}, session=session)
        wallets.update_one({"_id": dest_wallet["_id"]}, {"$inc": {"current_balance": dest_delta}}, session=session)
        doc["_id"] = result.inserted_id

    _run_atomically(_do)
    return doc


def _wallet_or_none(wallet_id):
    if wallet_id is None:
        return None
    return get_wallets_collection().find_one({"_id": wallet_id})


def reverse_transaction_balance_effect(txn: dict) -> None:
    """Un-applies a transaction's effect on wallet balance(s) — used before
    updating or deleting a transaction. Safe to call even if a referenced
    wallet has since been archived (still applies, since archiving doesn't
    delete the wallet doc)."""
    wallets = get_wallets_collection()

    if txn["type"] == "transfer":
        source = _wallet_or_none(txn.get("wallet_id"))
        dest = _wallet_or_none(txn.get("transfer_to_wallet_id"))

        def _do(session):
            if source:
                delta = reverse_delta(source["type"], "transfer", txn["amount"], role="source")
                wallets.update_one({"_id": source["_id"]}, {"$inc": {"current_balance": delta}}, session=session)
            if dest:
                delta = reverse_delta(dest["type"], "transfer", txn["amount"], role="destination")
                wallets.update_one({"_id": dest["_id"]}, {"$inc": {"current_balance": delta}}, session=session)

        _run_atomically(_do)
        return

    wallet = _wallet_or_none(txn.get("wallet_id"))
    if not wallet:
        return
    delta = reverse_delta(wallet["type"], txn["type"], txn["amount"])
    wallets.update_one({"_id": wallet["_id"]}, {"$inc": {"current_balance": delta}})


def delete_transaction(txn: dict) -> None:
    reverse_transaction_balance_effect(txn)
    get_transactions_collection().delete_one({"_id": txn["_id"]})


def update_single_wallet_transaction(old_txn: dict, new_wallet: dict, updates: dict) -> dict:
    """Reverses old_txn's balance effect, applies the merged fields' new
    effect against new_wallet, and persists the updated doc — all for
    expense/income transactions only (transfers/adjustments aren't editable
    through this path)."""
    transactions = get_transactions_collection()
    wallets = get_wallets_collection()

    old_wallet = _wallet_or_none(old_txn.get("wallet_id"))
    merged = {**old_txn, **updates}
    new_delta = compute_delta(new_wallet["type"], merged["type"], merged["amount"])

    def _do(session):
        if old_wallet:
            old_delta = reverse_delta(old_wallet["type"], old_txn["type"], old_txn["amount"])
            wallets.update_one({"_id": old_wallet["_id"]}, {"$inc": {"current_balance": old_delta}}, session=session)
        wallets.update_one({"_id": new_wallet["_id"]}, {"$inc": {"current_balance": new_delta}}, session=session)
        transactions.update_one({"_id": old_txn["_id"]}, {"$set": updates}, session=session)

    _run_atomically(_do)
    merged["updated_at"] = updates.get("updated_at", datetime.now(timezone.utc))
    return merged

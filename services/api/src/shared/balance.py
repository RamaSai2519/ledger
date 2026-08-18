"""Balance sign-convention math for the ledger's balance engine.

Sign convention (plan.md §6):
- bank_account / cash: positive current_balance = asset held.
- credit_card / pay_later / loan: positive current_balance = liability owed.

All deltas below are the amount to `$inc` a wallet's current_balance by,
given the wallet's type and the transaction affecting it. Reversing a
transaction (update/delete) is just applying the negated delta.
"""

LIABILITY_WALLET_TYPES = {"credit_card", "pay_later", "loan"}
ASSET_WALLET_TYPES = {"bank_account", "cash"}
WALLET_TYPES = ASSET_WALLET_TYPES | LIABILITY_WALLET_TYPES

TRANSACTION_TYPES = {"expense", "income", "transfer", "adjustment"}


def is_liability_wallet(wallet_type: str) -> bool:
    return wallet_type in LIABILITY_WALLET_TYPES


def compute_delta(wallet_type: str, txn_type: str, amount: float, role: str = "primary") -> float:
    """Delta to $inc a wallet's current_balance by for a transaction touching it.

    role is only meaningful for txn_type == "transfer": "source" (money
    leaving this wallet, behaves like an expense) or "destination" (money
    arriving at this wallet, behaves like income). For all other txn types
    role is ignored.

    Adjustment amounts are signed deltas themselves (unlike expense/income/
    transfer amounts, which are always positive) since a reconcile can move
    the balance in either direction.
    """
    is_liability = is_liability_wallet(wallet_type)

    if txn_type == "adjustment":
        return amount

    if txn_type == "expense" or (txn_type == "transfer" and role == "source"):
        return amount if is_liability else -amount

    if txn_type == "income" or (txn_type == "transfer" and role == "destination"):
        return -amount if is_liability else amount

    raise ValueError(f"unsupported_txn_type_for_balance_delta: {txn_type}")


def reverse_delta(wallet_type: str, txn_type: str, amount: float, role: str = "primary") -> float:
    return -compute_delta(wallet_type, txn_type, amount, role=role)

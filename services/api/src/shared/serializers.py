def _iso(value):
    return value.isoformat() if value else None


def _str_id(value):
    return str(value) if value is not None else None


def serialize_wallet(wallet: dict) -> dict:
    return {
        "id": _str_id(wallet["_id"]),
        "household_id": _str_id(wallet.get("household_id")),
        "name": wallet.get("name"),
        "type": wallet.get("type"),
        "provider": wallet.get("provider"),
        "account_last4": wallet.get("account_last4"),
        "opening_balance": wallet.get("opening_balance"),
        "current_balance": wallet.get("current_balance"),
        "currency": wallet.get("currency"),
        "icon": wallet.get("icon"),
        "color": wallet.get("color"),
        "is_archived": wallet.get("is_archived", False),
        "credit_card_details": wallet.get("credit_card_details"),
        "pay_later_details": wallet.get("pay_later_details"),
        "loan_details": wallet.get("loan_details"),
        "created_by": _str_id(wallet.get("created_by")),
        "created_at": _iso(wallet.get("created_at")),
        "updated_at": _iso(wallet.get("updated_at")),
    }


def serialize_category(category: dict) -> dict:
    return {
        "id": _str_id(category["_id"]),
        "household_id": _str_id(category.get("household_id")),
        "name": category.get("name"),
        "type": category.get("type"),
        "icon": category.get("icon"),
        "color": category.get("color"),
        "is_default": category.get("is_default", False),
        "is_archived": category.get("is_archived", False),
    }


def serialize_transaction(txn: dict) -> dict:
    return {
        "id": _str_id(txn["_id"]),
        "household_id": _str_id(txn.get("household_id")),
        "wallet_id": _str_id(txn.get("wallet_id")),
        "category_id": _str_id(txn.get("category_id")),
        "user_id": _str_id(txn.get("user_id")),
        "type": txn.get("type"),
        "amount": txn.get("amount"),
        "transfer_to_wallet_id": _str_id(txn.get("transfer_to_wallet_id")),
        "merchant_name": txn.get("merchant_name"),
        "note": txn.get("note"),
        "date": _iso(txn.get("date")),
        "source": txn.get("source"),
        "sms_id": _str_id(txn.get("sms_id")),
        "recurring_rule_id": _str_id(txn.get("recurring_rule_id")),
        "created_at": _iso(txn.get("created_at")),
        "updated_at": _iso(txn.get("updated_at")),
    }


def serialize_budget(budget: dict) -> dict:
    return {
        "id": _str_id(budget["_id"]),
        "household_id": _str_id(budget.get("household_id")),
        "scope": budget.get("scope"),
        "scope_ref_id": _str_id(budget.get("scope_ref_id")),
        "amount": budget.get("amount"),
        "period": budget.get("period", "monthly"),
        "threshold_percents": budget.get("threshold_percents", [80, 100]),
        "created_at": _iso(budget.get("created_at")),
        "updated_at": _iso(budget.get("updated_at")),
    }


def serialize_budget_progress(progress: dict) -> dict:
    return {
        "budget_id": _str_id(progress.get("budget_id")),
        "spent": progress.get("spent"),
        "amount": progress.get("amount"),
        "percent": progress.get("percent"),
        "period_start": _iso(progress.get("period_start")),
        "period_end": _iso(progress.get("period_end")),
        "thresholds": progress.get("thresholds"),
        "crossed_thresholds": progress.get("crossed_thresholds"),
    }


def serialize_notification(notification: dict) -> dict:
    return {
        "id": _str_id(notification["_id"]),
        "household_id": _str_id(notification.get("household_id")),
        "user_id": _str_id(notification.get("user_id")),
        "type": notification.get("type"),
        "payload": notification.get("payload", {}),
        "is_read": notification.get("is_read", False),
        "created_at": _iso(notification.get("created_at")),
    }

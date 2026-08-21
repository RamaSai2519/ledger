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
        "is_default": wallet.get("is_default", False),
        "credit_card_details": wallet.get("credit_card_details"),
        "pay_later_details": wallet.get("pay_later_details"),
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
        "sort_order": category.get("sort_order", 0),
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
        "loan_id": _str_id(txn.get("loan_id")),
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


def serialize_sms_inbox(sms: dict) -> dict:
    return {
        "id": _str_id(sms["_id"]),
        "household_id": _str_id(sms.get("household_id")),
        "user_id": _str_id(sms.get("user_id")),
        "sender_id": sms.get("sender_id"),
        "received_at": _iso(sms.get("received_at")),
        "parse_status": sms.get("parse_status"),
        "parsed_amount": sms.get("parsed_amount"),
        "parsed_direction": sms.get("parsed_direction"),
        "parsed_last4": sms.get("parsed_last4"),
        "parsed_merchant": sms.get("parsed_merchant"),
        "parsed_ref": sms.get("parsed_ref"),
        "suggested_wallet_id": _str_id(sms.get("suggested_wallet_id")),
        "suggested_category_id": _str_id(sms.get("suggested_category_id")),
        "wallet_confidence": sms.get("wallet_confidence", 0.0),
        "category_confidence": sms.get("category_confidence", 0.0),
        "confidence_score": sms.get("confidence_score"),
        # LED-18: layered parser output - transaction_type is one of the
        # full spec'd enum (upi_payment/imps/refund/emi_payment/...), while
        # parsed_direction stays debit/credit for existing balance-engine
        # code that only understands that binary. field_confidences/
        # parse_evidence make the confidence_score explainable rather than
        # a bare number (spec Part 13).
        "transaction_type": sms.get("transaction_type"),
        "transaction_status": sms.get("transaction_status"),
        "merchant_normalized": sms.get("merchant_normalized"),
        "counterparty": sms.get("counterparty"),
        "payment_method": sms.get("payment_method"),
        "balance_after": sms.get("balance_after"),
        "field_confidences": sms.get("field_confidences"),
        "parse_evidence": sms.get("parse_evidence"),
        "status": sms.get("status"),
        "resolved_transaction_id": _str_id(sms.get("resolved_transaction_id")),
        # raw_text is deliberately omitted (data minimization — never
        # round-trip raw SMS text back to the client beyond the initial
        # ingest request that sent it).
        "created_at": _iso(sms.get("created_at")),
        "updated_at": _iso(sms.get("updated_at")),
    }


def serialize_sms_parser_rule(rule: dict) -> dict:
    return {
        "id": _str_id(rule["_id"]),
        "household_id": _str_id(rule.get("household_id")),
        "bank_code": rule.get("bank_code"),
        "sender_ids": rule.get("sender_ids", []),
        "patterns": rule.get("patterns", []),
        "is_active": rule.get("is_active", True),
        "created_at": _iso(rule.get("created_at")),
        "updated_at": _iso(rule.get("updated_at")),
    }


def serialize_recurring_rule(rule: dict) -> dict:
    return {
        "id": _str_id(rule["_id"]),
        "household_id": _str_id(rule.get("household_id")),
        "wallet_id": _str_id(rule.get("wallet_id")),
        "category_id": _str_id(rule.get("category_id")),
        "type": rule.get("type"),
        "merchant_name": rule.get("merchant_name"),
        "amount": rule.get("amount"),
        "frequency": rule.get("frequency"),
        "next_due_date": _iso(rule.get("next_due_date")),
        "auto_detected": rule.get("auto_detected", False),
        "auto_create": rule.get("auto_create", False),
        "is_active": rule.get("is_active", True),
        "created_at": _iso(rule.get("created_at")),
        "updated_at": _iso(rule.get("updated_at")),
    }


def serialize_loan(loan: dict) -> dict:
    return {
        "id": _str_id(loan["_id"]),
        "household_id": _str_id(loan.get("household_id")),
        "name": loan.get("name"),
        "wallet_id": _str_id(loan.get("wallet_id")),
        "category_id": _str_id(loan.get("category_id")),
        "principal": loan.get("principal"),
        "annual_interest_rate": loan.get("annual_interest_rate"),
        "tenure_months": loan.get("tenure_months"),
        "emi_amount": loan.get("emi_amount"),
        "outstanding_balance": loan.get("outstanding_balance"),
        "start_date": _iso(loan.get("start_date")),
        "next_due_date": _iso(loan.get("next_due_date")),
        "is_active": loan.get("is_active", True),
        "created_at": _iso(loan.get("created_at")),
        "updated_at": _iso(loan.get("updated_at")),
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

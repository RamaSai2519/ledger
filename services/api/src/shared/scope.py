from bson import ObjectId

from shared.db import (
    get_budgets_collection,
    get_categories_collection,
    get_loans_collection,
    get_recurring_rules_collection,
    get_sms_inbox_collection,
    get_transactions_collection,
    get_users_collection,
)
from shared.output import NotFoundError, ValidationError


def require_household_id(user_id: str) -> ObjectId:
    """Looks up the requesting user's household_id — the household-scoping
    anchor for every wallet/category/transaction endpoint. Never trust a
    household_id passed in a request body; always derive it from the JWT
    subject's user doc so one household can never read/write another's data.
    """
    user = get_users_collection().find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("household_id"):
        raise NotFoundError("not_in_a_household")
    return user["household_id"]


def get_household_category(household_id: ObjectId, category_id: str) -> dict:
    try:
        oid = ObjectId(category_id)
    except Exception as exc:
        raise ValidationError("invalid_category_id") from exc
    category = get_categories_collection().find_one({"_id": oid, "household_id": household_id})
    if not category:
        raise NotFoundError("category_not_found")
    return category


def get_household_transaction(household_id: ObjectId, transaction_id: str) -> dict:
    try:
        oid = ObjectId(transaction_id)
    except Exception as exc:
        raise ValidationError("invalid_transaction_id") from exc
    txn = get_transactions_collection().find_one({"_id": oid, "household_id": household_id})
    if not txn:
        raise NotFoundError("transaction_not_found")
    return txn


def get_household_budget(household_id: ObjectId, budget_id: str) -> dict:
    try:
        oid = ObjectId(budget_id)
    except Exception as exc:
        raise ValidationError("invalid_budget_id") from exc
    budget = get_budgets_collection().find_one({"_id": oid, "household_id": household_id})
    if not budget:
        raise NotFoundError("budget_not_found")
    return budget


def get_household_sms_suggestion(household_id: ObjectId, sms_id: str) -> dict:
    try:
        oid = ObjectId(sms_id)
    except Exception as exc:
        raise ValidationError("invalid_sms_id") from exc
    sms = get_sms_inbox_collection().find_one({"_id": oid, "household_id": household_id})
    if not sms:
        raise NotFoundError("sms_suggestion_not_found")
    return sms


def get_household_recurring_rule(household_id: ObjectId, rule_id: str) -> dict:
    try:
        oid = ObjectId(rule_id)
    except Exception as exc:
        raise ValidationError("invalid_recurring_rule_id") from exc
    rule = get_recurring_rules_collection().find_one({"_id": oid, "household_id": household_id})
    if not rule:
        raise NotFoundError("recurring_rule_not_found")
    return rule


def get_household_loan(household_id: ObjectId, loan_id: str) -> dict:
    try:
        oid = ObjectId(loan_id)
    except Exception as exc:
        raise ValidationError("invalid_loan_id") from exc
    loan = get_loans_collection().find_one({"_id": oid, "household_id": household_id})
    if not loan:
        raise NotFoundError("loan_not_found")
    return loan

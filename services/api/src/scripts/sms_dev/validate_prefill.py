"""LED-19 acceptance-criteria check: run the latest sanitized real-device SMS
corpus (see `sms_dev pull`/`sanitize`) through the actual ingest pipeline
against a synthetic household seeded with one wallet per bank the corpus
contains, and report what fraction of parsed transactional SMS get a
non-null suggested_wallet_id / suggested_category_id.

Runs entirely against an in-memory mongomock DB (never touches a real
database) so it's safe to run repeatedly. Usage (from services/api/src):

    python -m scripts.sms_dev.validate_prefill
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import mongomock
import pymongo
from bson import ObjectId

import shared.db as db_module
from models.sms_ingest.compute import ingest_sms
from shared.category_keyword_rules_seed import seed_default_category_keyword_rules
from shared.merchant_aliases_seed import seed_default_merchant_aliases
from shared.sms_parser_rules_seed import default_sms_parser_rules, seed_default_sms_parser_rules
from shared.system_categories import get_or_create_balance_adjustment_category
from shared.constants import DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES
from scripts.sms_dev.cli import _load_latest_sanitized  # noqa: SLF001 - reuse the same "latest sanitized file" lookup


@dataclass
class _Input:
    raw_text: str
    sender_id: str
    received_at: str | None = None


def _seed_household_and_wallets() -> tuple[ObjectId, str]:
    household_id = ObjectId()
    now = datetime.now(timezone.utc)
    db_module.get_db()["households"].insert_one({"_id": household_id, "name": "Prefill Validation", "created_at": now})

    user_id = ObjectId()
    db_module.get_users_collection().insert_one(
        {"_id": user_id, "household_id": household_id, "mobile_number": "0000000000", "name": "Validator", "created_at": now}
    )

    categories = db_module.get_categories_collection()
    for name, icon in DEFAULT_EXPENSE_CATEGORIES:
        categories.insert_one({"household_id": household_id, "name": name, "type": "expense", "icon": icon, "is_default": True, "is_archived": False})
    for name, icon in DEFAULT_INCOME_CATEGORIES:
        categories.insert_one({"household_id": household_id, "name": name, "type": "income", "icon": icon, "is_default": True, "is_archived": False})
    get_or_create_balance_adjustment_category(household_id)

    wallets = db_module.get_wallets_collection()
    first_wallet_id = None
    for bank in default_sms_parser_rules():
        if bank.get("bank_code") == "GENERIC":
            continue
        wallet_type = "credit_card" if "credit card" in bank.get("institution_name", "").lower() or bank.get("bank_code") in {"ZET", "JUPITER", "AXIO"} else "bank_account"
        result = wallets.insert_one(
            {
                "household_id": household_id,
                "name": f"{bank['institution_name']} wallet",
                "type": wallet_type,
                "provider": bank["institution_name"],
                "account_last4": None,
                "opening_balance": 100000,
                "current_balance": 100000,
                "currency": "INR",
                "is_archived": False,
                "is_default": False,
                "created_at": now,
                "updated_at": now,
            }
        )
        if first_wallet_id is None:
            first_wallet_id = result.inserted_id

    # One wallet marked default so SMS from unrecognized/generic senders
    # still get a (low-confidence) wallet suggestion — mirrors what a real
    # household with a primary account would do.
    if first_wallet_id is not None:
        wallets.update_one({"_id": first_wallet_id}, {"$set": {"is_default": True}})

    return household_id, str(user_id)


def main() -> None:
    mock_client = mongomock.MongoClient()
    pymongo.MongoClient = lambda *a, **k: mock_client  # noqa: SLF001 - deliberate monkeypatch, script-local
    db_module._client = None

    seed_default_sms_parser_rules()
    seed_default_merchant_aliases()
    seed_default_category_keyword_rules()
    _household_id, user_id = _seed_household_and_wallets()

    messages = _load_latest_sanitized()
    total_transactional = 0
    wallet_hits = 0
    category_hits = 0

    for msg in messages:
        doc = ingest_sms(_Input(raw_text=msg["sanitized_text"], sender_id=msg["sender_id"]), user_id)
        if doc.get("parse_status") != "parsed" or doc.get("status") == "not_applicable":
            continue
        total_transactional += 1
        if doc.get("suggested_wallet_id"):
            wallet_hits += 1
        if doc.get("suggested_category_id"):
            category_hits += 1

    if total_transactional == 0:
        print("No transactional SMS parsed from the corpus - nothing to report.", file=sys.stderr)
        sys.exit(1)

    print(f"Parsed transactional SMS: {total_transactional}")
    print(f"suggested_wallet_id non-null:   {wallet_hits}/{total_transactional} ({100 * wallet_hits / total_transactional:.1f}%)")
    print(f"suggested_category_id non-null: {category_hits}/{total_transactional} ({100 * category_hits / total_transactional:.1f}%)")


if __name__ == "__main__":
    main()

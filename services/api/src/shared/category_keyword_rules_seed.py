"""Default `category_keyword_rules` seed data (LED-19) — a small, data-driven
set of merchant-keyword -> category heuristics for SMS category prefill's
layer 3 (spec: "keyword-based heuristic ... configurable, stored in a
collection or config, not hardcoded in parsing logic"), same "editable
without a release" spirit as `sms_parser_rules_seed.py`/`merchant_aliases_seed.py`.

Rules are global (household_id=None) by default; a household could in
principle get its own overrides later the same way sms_parser_rules layers
household-specific rules over global ones, but LED-19 only needs the global
set. Each rule's `category_name`/`category_type` names an existing default
category (shared/constants.py) so the rule is immediately useful without
requiring a new category to be created first — a rule whose category name
doesn't exist in a given household simply produces no match (graceful
degradation, not an error).
"""
from __future__ import annotations

from datetime import datetime, timezone

from shared.db import get_category_keyword_rules_collection

_RULES: list[dict] = [
    {
        "keywords": ["IRCTC", "RAILWAY", "INDIAN RAILWAYS", "UBER", "OLA", "MAKEMYTRIP", "GOIBIBO", "REDBUS"],
        "category_name": "Travel",
        "category_type": "expense",
    },
    {
        "keywords": ["MEDICAL", "PHARMACY", "PHARMA", "APOLLO", "HOSPITAL", "CLINIC"],
        "category_name": "Health & Fitness",
        "category_type": "expense",
    },
    {
        "keywords": ["ZERODHA", "GROWW", "ANGEL BROKING", "ANGEL ONE", "UPSTOX"],
        "category_name": "Investments",
        "category_type": "expense",
    },
    {
        "keywords": ["SWIGGY", "ZOMATO", "DOMINOS", "PIZZA", "EATERNITY", "FOOD"],
        "category_name": "Food & Dining",
        "category_type": "expense",
    },
    {
        "keywords": ["BIGBASKET", "BLINKIT", "ZEPTO", "DMART", "GROFERS", "INSTAMART", "GROCERY"],
        "category_name": "Groceries",
        "category_type": "expense",
    },
    {
        "keywords": ["PETROL", "DIESEL", "FUEL", "BPCL", "HPCL", "IOCL", "INDIAN OIL"],
        "category_name": "Fuel",
        "category_type": "expense",
    },
    {
        "keywords": ["AMAZON", "FLIPKART", "MYNTRA", "AJIO", "MEESHO"],
        "category_name": "Shopping",
        "category_type": "expense",
    },
    {
        "keywords": ["NETFLIX", "HOTSTAR", "SPOTIFY", "PRIME VIDEO", "JIOHOTSTAR", "SONYLIV"],
        "category_name": "Subscriptions",
        "category_type": "expense",
    },
    {
        "keywords": ["AIRTEL", "JIO", "VODAFONE", "VI ", "ELECTRICITY", "RECHARGE", "BROADBAND"],
        "category_name": "Bills & Utilities",
        "category_type": "expense",
    },
]


def default_category_keyword_rules() -> list[dict]:
    return [
        {
            "rule_key": rule["category_name"].lower().replace(" ", "_").replace("&", "and"),
            "keywords": rule["keywords"],
            "category_name": rule["category_name"],
            "category_type": rule["category_type"],
            "household_id": None,
            "is_active": True,
        }
        for rule in _RULES
    ]


def seed_default_category_keyword_rules() -> int:
    collection = get_category_keyword_rules_collection()
    now = datetime.now(timezone.utc)
    count = 0
    for doc in default_category_keyword_rules():
        collection.update_one(
            {"rule_key": doc["rule_key"], "household_id": None},
            {"$set": {**doc, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        count += 1
    return count

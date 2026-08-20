"""Default `merchant_aliases` seed data (LED-18, spec Part 7) — common raw
merchant string variants seen in real bank SMS mapped to one canonical
display name. Grows over time from real corrections (see
`scripts/sms_dev/cli.py review`), same "data-driven, editable without a
release" spirit as `sms_parser_rules_seed.py`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from shared.db import get_merchant_alias_collection
from shared.sms.merchant_normalizer import normalize_key

_ALIASES: dict[str, list[str]] = {
    "Amazon": ["AMAZON", "AMAZON MKTPLACE", "AMZN", "AMAZON RETAIL", "AMAZON.IN"],
    "Swiggy": ["SWIGGY", "SWIGGY*BLR", "SWIGGY BANGALORE", "BUNDL TECHNOLOGIES"],
    "Zomato": ["ZOMATO", "ZOMATO LTD", "ZOMATO ONLINE"],
    "Flipkart": ["FLIPKART", "FLIPKART INTERNET", "FKRT"],
    "Netflix": ["NETFLIX", "NETFLIX.COM"],
    "BigBasket": ["BIGBASKET", "BIG BASKET", "SUPERMARKET GROCERY"],
    "Reliance Fresh": ["RELIANCE FRESH", "RELIANCE RETAIL"],
    "Uber": ["UBER", "UBER INDIA", "UBER TRIP"],
    "Ola": ["OLA", "OLA CABS", "ANI TECHNOLOGIES"],
}


def default_merchant_aliases() -> list[dict]:
    docs = []
    for canonical, variants in _ALIASES.items():
        for variant in variants:
            docs.append({"raw_key": normalize_key(variant), "raw_variant": variant, "canonical_name": canonical})
    return docs


def seed_default_merchant_aliases() -> int:
    collection = get_merchant_alias_collection()
    now = datetime.now(timezone.utc)
    count = 0
    for doc in default_merchant_aliases():
        collection.update_one(
            {"raw_key": doc["raw_key"]},
            {"$set": {**doc, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        count += 1
    return count

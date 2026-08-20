"""One-off, idempotent backfill for existing `categories` documents created
before LED-15 added a `sort_order` field. Categories were previously always
listed alphabetically by name, so this preserves that as the initial order:
per household, categories are numbered 0..N-1 in the same alphabetical
order they were already displayed in.

Only touches documents with no `sort_order` set (missing or None) — never
overwrites a custom order a household may already have from using the
reorder endpoint.

Usage (from services/api/src, with MONGO_URI/MONGO_DB_NAME configured):

    python -m scripts.backfill_category_sort_order
"""
import logging

from shared.db import get_categories_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    categories = get_categories_collection()

    household_ids = categories.distinct(
        "household_id", {"$or": [{"sort_order": {"$exists": False}}, {"sort_order": None}]}
    )

    total_updated = 0
    for household_id in household_ids:
        docs = list(categories.find({"household_id": household_id}).sort("name", 1))
        for i, doc in enumerate(docs):
            if doc.get("sort_order") is not None:
                continue
            categories.update_one({"_id": doc["_id"]}, {"$set": {"sort_order": i}})
            total_updated += 1
        logger.info("household_id=%s: set sort_order on %d categories", household_id, len(docs))

    logger.info("backfilled sort_order on %d categories doc(s) total", total_updated)


if __name__ == "__main__":
    main()

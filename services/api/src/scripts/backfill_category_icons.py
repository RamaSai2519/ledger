"""One-off, idempotent backfill for existing `categories` documents created
before LED-12 added icon keys to shared/constants.py's
DEFAULT_EXPENSE_CATEGORIES/DEFAULT_INCOME_CATEGORIES — those households'
default categories were seeded with no `icon` field at all.

Matches purely by category name against the same name -> icon-key mapping
household_create/compute.py now seeds new households with, and only
touches documents with no `icon` set (missing, None, or empty string) —
never overwrites a custom icon a household may already have.

Usage (from services/api/src, with MONGO_URI/MONGO_DB_NAME configured):

    python -m scripts.backfill_category_icons
"""
import logging

from shared.constants import DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES
from shared.db import get_categories_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    icon_by_name = dict(DEFAULT_EXPENSE_CATEGORIES) | dict(DEFAULT_INCOME_CATEGORIES)
    categories = get_categories_collection()

    total_matched = 0
    for name, icon in icon_by_name.items():
        result = categories.update_many(
            {"name": name, "$or": [{"icon": {"$exists": False}}, {"icon": None}, {"icon": ""}]},
            {"$set": {"icon": icon}},
        )
        if result.modified_count:
            logger.info("categories.name=%r: set icon=%r on %d doc(s)", name, icon, result.modified_count)
        total_matched += result.modified_count

    logger.info("backfilled icon on %d categories doc(s) total", total_matched)


if __name__ == "__main__":
    main()

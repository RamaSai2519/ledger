"""One-off/idempotent runner for seeding the global (household_id=None)
`category_keyword_rules` collection (LED-19) — see
shared/category_keyword_rules_seed.py for the actual rule data and the
upsert logic (keyed by rule_key, safe to rerun).

Usage (from services/api/src, with MONGO_URI/MONGO_DB_NAME configured, e.g.
via pipenv run):

    python -m scripts.seed_category_keyword_rules
"""
import logging

from shared.category_keyword_rules_seed import seed_default_category_keyword_rules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    count = seed_default_category_keyword_rules()
    logger.info("seeded/updated %d category_keyword_rules doc(s)", count)


if __name__ == "__main__":
    main()

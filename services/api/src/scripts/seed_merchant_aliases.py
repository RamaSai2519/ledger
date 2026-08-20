"""One-off/idempotent runner for seeding the global `merchant_aliases`
collection (LED-18) — see shared/merchant_aliases_seed.py for the actual
alias data and the upsert logic (keyed by raw_key, safe to rerun).

Usage (from services/api/src, with MONGO_URI/MONGO_DB_NAME configured, e.g.
via pipenv run):

    python -m scripts.seed_merchant_aliases
"""
import logging

from shared.merchant_aliases_seed import seed_default_merchant_aliases

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    count = seed_default_merchant_aliases()
    logger.info("seeded/updated %d merchant_aliases doc(s)", count)


if __name__ == "__main__":
    main()

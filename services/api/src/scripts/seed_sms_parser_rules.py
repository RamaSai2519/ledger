"""One-off/idempotent runner for seeding the global (household_id=None)
`sms_parser_rules` collection (plan.md §7, §12, LED-7) — see
shared/sms_parser_rules_seed.py for the actual rule data and the upsert
logic (keyed by bank_code, safe to rerun).

Usage (from services/api/src, with MONGO_URI/MONGO_DB_NAME configured, e.g.
via pipenv run):

    python -m scripts.seed_sms_parser_rules
"""
import logging

from shared.sms_parser_rules_seed import seed_default_sms_parser_rules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    count = seed_default_sms_parser_rules()
    logger.info("seeded/updated %d sms_parser_rules doc(s)", count)


if __name__ == "__main__":
    main()

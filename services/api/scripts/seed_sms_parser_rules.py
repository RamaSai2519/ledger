#!/usr/bin/env python3
"""One-time (idempotent, safe to re-run) seed of the global `sms_parser_rules`
collection for the 8 target banks + generic fallback (plan.md §12, LED-7).

Unlike default categories (seeded per-household on household_create, since
each household needs its own copy), sms_parser_rules' defaults are global
(household_id=None) and shared by every household — so this is a standalone
script rather than something wired into a per-household creation path.

Usage (from services/api/src, same venv as the app):
    PIPENV_IGNORE_VIRTUALENVS=1 pipenv run python ../scripts/seed_sms_parser_rules.py

Run once against each environment's MongoDB (local/dev/prod Atlas) after
deploy, or whenever the seed data in shared/sms_parser_rules_seed.py changes.
Not invoked automatically by the Lambda handler or CI — the household/user
data model in this repo assumes a human runs data-migration-shaped scripts
deliberately (see CLAUDE.md's Terraform-apply-by-hand carve-out for the same
reasoning applied to infra).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from shared.sms_parser_rules_seed import seed_default_sms_parser_rules  # noqa: E402


def main() -> None:
    count = seed_default_sms_parser_rules()
    print(f"seeded/updated {count} global sms_parser_rules document(s)")


if __name__ == "__main__":
    main()

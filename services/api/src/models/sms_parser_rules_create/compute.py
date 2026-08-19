from datetime import datetime, timezone

from bson import ObjectId

from shared.db import get_sms_parser_rules_collection


def create_parser_rule(inp, household_id: ObjectId) -> dict:
    # Household-scoped only — global (household_id=None) rules are seed-only
    # (shared/sms_parser_rules_seed.py) and never created through this
    # endpoint, per shared/sms_parsing.py's find_matching_rules precedence
    # (household rules checked before global ones).
    now = datetime.now(timezone.utc)
    doc = {
        "household_id": household_id,
        "bank_code": inp.bank_code,
        "sender_ids": inp.sender_ids,
        "patterns": inp.patterns,
        "is_active": inp.is_active,
        "created_at": now,
        "updated_at": now,
    }
    result = get_sms_parser_rules_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

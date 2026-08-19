
from shared.db import get_sms_parser_rules_collection
from shared.interfaces import SmsParserRulesListInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_sms_parser_rule


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    # Both the household's own custom rules AND the global (household_id=None)
    # seeded rules, so a household can see what already exists before adding
    # a custom override (see shared/sms_parsing.py's find_matching_rules,
    # which checks household rules first, global rules second).
    query = {"$or": [{"household_id": household_id}, {"household_id": None}]}
    docs = list(get_sms_parser_rules_collection().find(query).sort("bank_code", 1))
    return success({"rules": [serialize_sms_parser_rule(d) for d in docs]})

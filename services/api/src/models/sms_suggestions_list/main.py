
from shared.db import get_sms_inbox_collection
from shared.interfaces import SmsSuggestionsListInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_sms_inbox


def process(inp: Input):
    household_id = require_household_id(inp.user_id)
    query = {"household_id": household_id, "status": "suggested"}

    docs = list(get_sms_inbox_collection().find(query).sort("received_at", -1))
    return success({"suggestions": [serialize_sms_inbox(d) for d in docs]})

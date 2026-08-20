from models.loan_list import validate
from shared.db import get_loans_collection
from shared.interfaces import LoanListInput as Input
from shared.output import success
from shared.scope import require_household_id
from shared.serializers import serialize_loan


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)

    mongo_query = {"household_id": household_id}
    if inp.is_active is not None:
        mongo_query["is_active"] = inp.is_active.lower() == "true"

    loans = list(get_loans_collection().find(mongo_query).sort("created_at", 1))
    return success({"loans": [serialize_loan(l) for l in loans]})

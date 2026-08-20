from models.category_reorder import compute, validate
from shared.interfaces import CategoryReorderInput as Input
from shared.output import success
from shared.scope import require_household_id


def process(inp: Input):
    validate.validate(inp)
    household_id = require_household_id(inp.user_id)
    categories = compute.reorder_categories(inp, household_id)
    return success({"categories": categories})

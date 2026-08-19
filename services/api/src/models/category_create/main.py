from models.category_create import compute, validate
from shared.interfaces import CategoryCreateInput as Input
from shared.output import success
from shared.serializers import serialize_category


def process(inp: Input):
    validate.validate(inp)
    category = compute.create_category(inp, inp.user_id)
    return success(serialize_category(category))

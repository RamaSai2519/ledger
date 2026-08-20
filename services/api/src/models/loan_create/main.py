from models.loan_create import compute, validate
from shared.interfaces import LoanCreateInput as Input
from shared.output import success
from shared.serializers import serialize_loan


def process(inp: Input):
    validate.validate(inp)
    loan = compute.create_loan(inp, inp.user_id)
    return success(serialize_loan(loan))

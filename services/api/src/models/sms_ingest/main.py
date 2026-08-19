from models.sms_ingest import compute, validate
from shared.interfaces import SmsIngestInput as Input
from shared.output import success
from shared.serializers import serialize_sms_inbox


def process(inp: Input):
    validate.validate(inp)
    doc = compute.ingest_sms(inp, inp.user_id)
    return success(serialize_sms_inbox(doc))

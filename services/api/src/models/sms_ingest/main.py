from dataclasses import dataclass

from models.sms_ingest import compute, validate
from shared.output import success
from shared.serializers import serialize_sms_inbox


@dataclass
class Input:
    raw_text: str
    sender_id: str
    received_at: str | None = None


def process(request_json: dict, user_id: str):
    inp = Input(**request_json)
    validate.validate(inp)
    doc = compute.ingest_sms(inp, user_id)
    return success(serialize_sms_inbox(doc))

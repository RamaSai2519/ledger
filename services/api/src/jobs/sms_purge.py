"""Raw SMS text purge job (plan.md §2.3/§14, LED-7).

Data minimization: raw SMS text is only needed transiently, to parse a
suggestion and let a human resolve it. Once a suggestion is resolved
(accepted/dismissed) — or 30 days have passed regardless of resolution —
the raw text is nulled out, but the rest of the doc (structured parsed
fields, status, resolved_transaction_id, etc.) is kept for audit history,
per plan.md's explicit instruction not to delete the whole doc.

Not wired to an in-process scheduler for the same reason as
jobs/budget_threshold_check.py (zip-deployed Lambda behind API Gateway, no
persistent process) — invoked by index.py's `scheduled_handler` on an
EventBridge Scheduler trigger (infra/terraform/scheduler.tf).
"""
import logging
from datetime import datetime, timedelta, timezone

from shared.db import get_sms_inbox_collection

logger = logging.getLogger(__name__)

RAW_TEXT_RETENTION_DAYS = 30


def run_sms_purge() -> list:
    """Nulls raw_text on every sms_inbox doc that either isn't still an
    unresolved suggestion, or has aged past the retention window regardless
    of status. Returns the list of purged sms _ids."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RAW_TEXT_RETENTION_DAYS)
    inbox = get_sms_inbox_collection()

    query = {
        "raw_text": {"$ne": None},
        "$or": [
            {"status": {"$ne": "suggested"}},
            {"created_at": {"$lt": cutoff}},
        ],
    }

    purged_ids = [doc["_id"] for doc in inbox.find(query, {"_id": 1})]
    if purged_ids:
        inbox.update_many({"_id": {"$in": purged_ids}}, {"$set": {"raw_text": None}})
        logger.info("purged raw_text on %d sms_inbox doc(s)", len(purged_ids))

    return purged_ids

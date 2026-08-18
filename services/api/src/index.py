import logging
from datetime import datetime, timezone

import awsgi
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_restful import Api

from jobs.bill_due_reminders import run_bill_due_reminders
from jobs.budget_threshold_check import run_budget_threshold_check
from jobs.digest_notifications import run_daily_digest
from jobs.net_worth_snapshot import run_net_worth_snapshot
from shared.after_request import register_error_handlers
from shared.configs import CONFIG
from shared.db import get_revoked_tokens_collection
from services.controller import register_routes

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = CONFIG["jwt_secret_key"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = CONFIG["access_token_minutes"] * 60
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = CONFIG["refresh_token_days"] * 24 * 60 * 60

jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def _check_if_token_revoked(jwt_header, jwt_payload) -> bool:
    revoked = get_revoked_tokens_collection().find_one({"jti": jwt_payload["jti"]})
    return revoked is not None


register_error_handlers(app)

api = Api(app)
register_routes(api)


# Job name -> callable. Dispatched by `scheduled_handler` below, invoked by
# EventBridge Scheduler (infra/terraform/scheduler.tf) rather than an
# in-process scheduler — see docs/decisions/0005-eventbridge-scheduler-for-jobs.md.
# Each job function is also directly importable/callable/unit-testable on
# its own (jobs/*.py), independent of this dispatch table.
SCHEDULED_JOBS = {
    "budget_threshold_check": run_budget_threshold_check,
    "digest_notifications": run_daily_digest,
    "bill_due_reminders": run_bill_due_reminders,
    "net_worth_snapshot": run_net_worth_snapshot,
}


def scheduled_handler(event, context):
    """Invoked for EventBridge Scheduler-triggered runs. `event` is the JSON
    payload configured on each aws_scheduler_schedule resource's target
    input: {"job": "<job name>"}. Kept as its own function (rather than
    inlined into `handler`) so it stays directly unit-testable."""
    job_name = (event or {}).get("job")
    job_fn = SCHEDULED_JOBS.get(job_name)
    if job_fn is None:
        logger.error("scheduled_handler received unknown job: %r", job_name)
        return {"status": "FAILURE", "error": f"unknown_job: {job_name}"}

    result = job_fn()
    logger.info("scheduled job %r completed: %d item(s)", job_name, len(result))
    return {"status": "SUCCESS", "job": job_name, "count": len(result)}


def handler(event, context):
    # A single Lambda function (`ledger-api`, see infra/terraform/lambda.tf)
    # serves both the API Gateway proxy integration and EventBridge
    # Scheduler-triggered job runs — API Gateway's proxy event always has a
    # top-level "httpMethod" (payload_format_version = "1.0"; see
    # api_gateway.tf), while a Scheduler invocation's event is just the
    # plain JSON input {"job": "..."} configured on the schedule. Dispatch
    # on that shape rather than needing two separately-deployed functions.
    if isinstance(event, dict) and "job" in event and "httpMethod" not in event:
        return scheduled_handler(event, context)
    return awsgi.response(app, event, context)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=CONFIG["debug"])

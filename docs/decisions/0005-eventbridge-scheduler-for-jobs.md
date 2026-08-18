# ADR 0005: EventBridge Scheduler for background jobs, not APScheduler

**Status:** Accepted

## Context

plan.md §3/§15 specifies "APScheduler (MVP) → Celery/Redis later" for
scheduled jobs (budget threshold checks, the daily digest, bill-due
reminders — plan.md §8). That plan was written before the deployment
target was finalized as a zip-deployed AWS Lambda behind API Gateway
(ADR 0003): `services/api/src/index.py`'s `handler(event, context)` is
invoked per-request by API Gateway and the process exits/freezes between
invocations — there is no persistent process for an in-process scheduler
like APScheduler to run its background thread in. APScheduler's jobs would
simply never fire on this deployment shape.

## Decision

- Each scheduled job's logic lives as a plain, directly-callable,
  unit-tested Python function in `services/api/src/jobs/` (same pattern as
  the LED-4 `jobs/balance_reconciliation.py`):
  - `jobs/budget_threshold_check.py`
  - `jobs/digest_notifications.py`
  - `jobs/bill_due_reminders.py`
- `index.py` exposes a `scheduled_handler(event, context)` that dispatches
  on `event["job"]` to the matching function. The Lambda's single configured
  entrypoint, `handler`, distinguishes an API Gateway proxy event (has
  `httpMethod`, per the v1.0 payload format ADR 0003 pins) from an
  EventBridge Scheduler invocation (plain `{"job": "..."}` payload, no
  `httpMethod`) and dispatches accordingly — one Lambda function serves
  both integrations, no second deployed function to keep in sync.
- `infra/terraform/scheduler.tf` provisions three `aws_scheduler_schedule`
  resources (one per job) targeting the existing `ledger-api` Lambda
  function, an IAM execution role (`ledger-scheduler`) EventBridge
  Scheduler assumes to invoke it, and an `aws_lambda_permission` granting
  `scheduler.amazonaws.com` the right to invoke `ledger-api`.

## Consequences

- No new Lambda function, no Celery/Redis infrastructure — the deviation
  from plan.md's literal wording stays within "one Lambda, managed
  scheduler triggers it," which is the smallest change consistent with
  ADR 0003's zip-Lambda decision.
- The GitHub Actions deploy role's IAM policy needs incremental extension
  (per CLAUDE.md's "extend incrementally, never widen to `*`" rule) with
  `scheduler:CreateSchedule`, `scheduler:UpdateSchedule`,
  `scheduler:DeleteSchedule`, `scheduler:GetSchedule`, and `iam:PassRole`
  scoped to the new `ledger-scheduler` role's ARN, before `terraform apply`
  in CI can manage these resources — a manual, one-time IAM change the repo
  owner applies themselves (same category as the OIDC role bootstrap),
  not something Terraform or CI can grant itself.
- If job volume or duration ever outgrows what fits in periodic Lambda
  invocations, the natural next step is the same one plan.md already names
  for scale: Celery/Redis (or SQS+Lambda), not "add APScheduler back" —
  this deployment shape never supports an in-process scheduler.

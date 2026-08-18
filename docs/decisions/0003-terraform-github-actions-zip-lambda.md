# ADR 0003: Terraform + GitHub Actions, zip-deployed Lambda

**Status:** Accepted

## Context

The user specified Terraform-managed, zip-deployed Lambda deployment,
following the pattern already proven in `~/Projects/journeymen` (which
itself moved from a container-image/ECR Lambda to a zip deploy — see that
repo's ADR 0015 — after finding the container image added deploy latency
and ECR management overhead with no benefit for a Flask app this size).

## Decision

- `services/api/scripts/build_lambda_zip.sh` builds a Lambda deployment zip
  by `pip install --target`-ing pinned dependency versions as
  `manylinux2014_x86_64` wheels (matching the Lambda runtime regardless of
  build host), then copying in `index.py`/`shared/`/`services/`/`models/`.
- `infra/terraform/` provisions one zip-deployed Lambda (`ledger-api`) and
  an HTTP API Gateway (`ANY /{proxy+}`, `payload_format_version = "1.0"` —
  required because `aws-wsgi` only understands the v1.0 REST-API-style
  event shape, not HttpApi's v2.0 default).
- `.github/workflows/deploy-api.yml` builds the zip and applies Terraform on
  every push to `master` touching `services/api/**`/`infra/terraform/**`,
  authenticating via GitHub OIDC role assumption — no long-lived AWS keys
  in CI.
- State backend (S3 + DynamoDB lock table) and the OIDC deploy role are
  bootstrapped once by hand (`infra/terraform/README.md`), not by CI.

## Consequences

- Routine deploys never need `terraform apply` run by hand.
- The deploy role's policy is scoped to exactly `ledger-*`-named resources,
  extended (a new `iam put-role-policy` statement) only when Terraform
  config grows to manage a new resource type — never widened to `*`.
- Resources are isolated (distinct names, distinct Terraform state key) from
  the `journeymen` project, which deploys into the same AWS account.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Phase 0 (monorepo scaffold) and Phase 1 (auth & household) are built, tested, and deployed live — see the root [`README.md`](README.md) for the live API URL and current status. Phases 2-7 are tracked as Jira issues under project **LED** (see below), not yet built.

- `plan.md` — full backend + mobile implementation plan (data model, API reference, phased roadmap)
- `DESIGN_BRIEF.md` — visual/UX design brief; the actual mockups it produced live in the Claude Design project linked under "Design reference" below, not as files in this repo

Backend: `cd services/api/src && pipenv install && pipenv run pytest -v`. Mobile: `cd apps/mobile && npm install && npm run typecheck`. See each directory's own README for the full command list and layout.

## What this project is

**Ledger** — a private household expense tracker for two people sharing one pooled ledger (no expense-splitting/settle-up). Each partner has a separate login but sees the exact same shared data. Android-only mobile app + Flask/MongoDB backend. The standout feature is background parsing of incoming bank SMS to auto-suggest transactions via push notification.

Full product/architecture detail lives in `plan.md`; read it before scaffolding the backend or mobile app. Key points to know going in:

### Tech stack (planned)
- **Backend:** Python 3.12, Flask (Blueprints), PyMongo, Flask-JWT-Extended, Pydantic/Marshmallow, APScheduler (MVP) → Celery/Redis later, Firebase Admin SDK for FCM, Gunicorn + Nginx in Docker, MongoDB Atlas, deployed on AWS.
- **Mobile:** React Native (bare workflow — required for a custom native SMS module, not Expo-managed), React Navigation, TanStack Query (server state) + Zustand (local UI state), a custom Kotlin `BroadcastReceiver` native module for SMS, `@react-native-firebase/messaging`, `react-native-biometrics`, encrypted local storage for tokens/PIN.

### Non-negotiable constraints (from plan.md §2)
1. **Play Store SMS policy**: general apps can't get broad `READ_SMS`/`RECEIVE_SMS` approval for public listing. Distribute via sideloaded APK or Play Console Internal Testing track only — never plan for open Play Store release while SMS reading exists.
2. **SMS parsing must be data-driven**, not hardcoded — bank message formats change without notice, so parser rules live in the `sms_parser_rules` MongoDB collection (editable without a release).
3. **Data minimization**: only forward SMS from a curated bank/sender allow-list (filtered client-side before it ever leaves the device); purge raw SMS text after ~30 days or resolution.
4. Use **MongoDB Atlas**, not self-hosted Mongo.

### Core domain model
All collections are scoped by `household_id` except `users`. See `plan.md` §4 for full field-level schemas of `users`, `households`, `wallets`, `categories`, `transactions`, `recurring_rules`, `budgets`, `notifications`, `sms_inbox`, `merchant_category_map`, `sms_parser_rules`, `net_worth_snapshots`.

Things that are easy to get wrong if you don't read the plan first:
- **Balance sign convention**: for `bank_account`/`cash`, positive `current_balance` = asset. For `credit_card`/`pay_later`/`loan`, positive = liability owed. Net worth = Σassets − Σliabilities.
- **`current_balance` is a cached field**, atomically maintained via `$inc` on every transaction write, wrapped in a Mongo multi-document transaction for transfers (two wallets touched at once). A nightly job recomputes from `opening_balance` + transaction history and flags drift as a correctness safety net — don't let the cached field silently diverge.
- **Manual reconcile never silently overwrites a balance** — it computes the delta and inserts an `adjustment`-type transaction against a system "Balance Adjustment" category, so the ledger stays internally consistent and auditable.
- **SMS pipeline dedup**: before creating a suggestion, check for an existing transaction on the same wallet with a similar amount within the same day; if found, silently link `sms_id` to it instead of prompting again.
- **The "learning" mechanism** for SMS category suggestions is simple frequency-based matching via `merchant_category_map` (normalized merchant string → category/wallet, incremented on confirm) — no ML, intentionally.
- Net worth history is served from a **daily snapshot job** (`net_worth_snapshots`), not computed on the fly, since historical net worth requires replaying all transactions up to a date.

### API surface
Base path `/api`; full route table (auth, users, wallets, categories, transactions, recurring, budgets, insights, sms, notifications) is in `plan.md` §11.

### Build order
The plan defines a phased roadmap (§15): Setup → Auth & Household → Core Ledger (wallets/categories/transactions/balance engine) → Budgets & Notifications → Insights → SMS Pipeline → Recurring Transactions → Polish & Ship. Follow this order when scaffolding — later phases (SMS, recurring) assume the ledger and auth foundations from earlier phases exist.

## Jira task tracking — required

Jira is the source of truth for project work: space **Ledger**, project key **LED**.

- Before starting implementation, check Jira for the relevant issue and its current status using the Atlassian Rovo MCP tools.
- If no issue covers the requested work, file a `LED` Jira issue before implementation with a clear title, scope, and acceptance criteria.
- Move the issue to `In Progress` when work begins. Add progress comments when they provide useful handoff context.
- After implementation, add a concise comment with the change and validation performed. Move it to `In Review`; only move it to `Done` after it is merged or deployed.

## Deployment: Terraform + zip-deployed Lambda (backend)

The backend deploys to AWS Lambda as a **zip package** (not a container image), applied via **Terraform**, following the pattern used in `~/Projects/journeymen` (`infra/terraform/`, `services/api/scripts/build_lambda_zip.sh`, `.github/workflows/deploy-api.yml`) — consult that repo directly for concrete file shapes when scaffolding this one, rather than reinventing the pattern. Key conventions to carry over:

- **Build script** (`scripts/build_lambda_zip.sh`) `pip install --target`s pinned dependency versions as `manylinux2014_x86_64` wheels matching the Lambda runtime's Python version/arch, then copies in application source — kept in sync by hand with the Pipfile/requirements source of truth, not auto-derived. `boto3`/`botocore` are excluded (the managed Lambda runtime already bundles them).
- **Terraform module** (`infra/terraform/`) typically splits into `versions.tf` (provider pins + S3 backend), `providers.tf`, `variables.tf` (including sensitive secrets, never hardcoded), `iam.tf` (least-privilege execution roles), `lambda.tf`, `api_gateway.tf` (HTTP API, `ANY /{proxy+}` route — **if using `aws-wsgi`/similar REST-shape adapters, pin `payload_format_version = "1.0"`**, since API Gateway v2 defaults to a v2.0 event payload those adapters don't understand), `outputs.tf`.
- **State backend**: S3 bucket (versioned, encrypted, public access blocked) + DynamoDB lock table, bootstrapped once by hand (not by CI) — see journeymen's `infra/terraform/README.md` §"One-time bootstrap" for the exact commands to adapt.
- **CI auth**: GitHub Actions OIDC role assumption (`aws-actions/configure-aws-credentials` with `role-to-assume`), never long-lived AWS access keys. The deploy role's policy is scoped tightly to this stack's named resources, extended incrementally (a new `iam put-role-policy` statement) whenever Terraform config grows to manage a new resource type — not widened to `*`.
- **Nothing here should be `terraform apply`'d by hand for routine deploys** — only for the one-time bootstrap or local debugging. Routine deploys go through the GitHub Actions workflow on push to the main branch.
- If the Lambda's build context can't reach a shared package living elsewhere in the monorepo (e.g. a `packages/` workspace), vendor it as committed plain source via a small sync script (`scripts/vendor-*.sh`) rather than a path dependency — same reasoning as journeymen's `shared_types`/`scoring` vendoring.
- Don't invent Terraform resources, scripts, or workflow files as "should exist" — check what's actually been scaffolded in this repo before referencing it, the same rule journeymen's own CLAUDE.md states about itself.

## AWS guidance

- Prefer the AWS MCP Server for AWS interactions — it provides sandboxed execution, observability, and audit logging. Fall back to the AWS CLI directly only if unavailable.
- Before starting an AWS-related task, check whether a relevant AWS skill is available and load it with `retrieve_skill`; prefer its guidance over general knowledge.
- Verify uncertain AWS details (API parameters, permissions, limits, error codes) against documentation rather than guessing; state uncertainty explicitly if unconfirmed.
- Prefer infrastructure-as-code (Terraform, per the deployment convention above) over direct CLI mutation of AWS resources.
- Follow AWS Well-Architected Framework principles when designing infrastructure.
- Do not use em dashes in AWS resource names or descriptions — use hyphens.

## Secret safety

- Load the `aws-secrets-manager` skill first for any task touching a secret, credential, API key, token, or password.
- Never call `secretsmanager get-secret-value`/`batch-get-secret-value` directly, and never hit the Secrets Manager Agent daemon directly.
- Use `{{resolve:secretsmanager:secret-id:SecretString:json-key}}` with `asm-exec` so a secret resolves at runtime without ever entering the model's context window.
- Application secrets (JWT signing key, OAuth/API client secrets, DB URI) are passed into Lambda as Terraform variables sourced from GitHub Actions repo secrets — never hardcoded into `.tf` files or committed `.env` files. Any secret exposed in git history (e.g. from an earlier deployment approach) must be rotated, not just relocated.

## Testing — required for backend endpoints

Any API endpoint added or changed must ship with tests in the same change — no exception for "it's just a stub." Cover at minimum the success path, the validation-failure path, and any referential-integrity or security check the endpoint performs (e.g. the SMS data-minimization/allow-list guard, household-scoping on every collection). Prefer a real test client against an in-memory/mocked datastore (e.g. `mongomock` for MongoDB) over hitting a live database in tests.

## Design reference

`DESIGN_BRIEF.md` specifies a dark-theme Android UI (near-black base `#0B0B12`, indigo hero accent `#5B54F9`, green/red positive/negative accents) with a signature **dual-identity accent system** — each of the two partners gets a distinct accent hue shown as a thin edge/ring/tag on transactions they logged, since this is a joint ledger rather than a solo finance app. When building UI, prefer this over a generic single-accent dark fintech look. Typography uses three distinct roles: a display face for hero numbers, a neutral sans for body text, and a **tabular-figure face specifically for monetary amounts** so columns of numbers align.

The brief's high-fidelity screens live in a Claude Design project, not as files in this repo:
**https://claude.ai/design/p/4e2b7218-8fbc-41c1-af26-2058b55579b2?file=Khaata+App.dc.html**

Before implementing any screen, pull the actual mockup rather than re-deriving it from the token summary above:

1. Use the `claude_design` MCP (`https://api.anthropic.com/v1/design/mcp`, authenticate via `/design-login`) to read the project. The whole project is readable, not just the linked file.
2. Focus on `Khaata App.dc.html` for the actual screen designs — component layout, spacing, copy, states (empty/loading/error) per screen.
3. That file imports two support files, also worth reading for context: `android-frame.jsx` (the Android device-frame/status-bar/nav-bar chrome the mockups are composed inside — not app code, just the mockup's presentation shell) and `support.js` (Claude Design's canvas runtime — infrastructure, not design content, safe to skip unless something about how the canvas renders is unclear).
4. The project still refers to the product by its original working name, **Khaata** — that name is retired in favor of **Ledger** everywhere else (repo, package names, AWS resources, Jira). Don't propagate "Khaata" into new code or docs; treat it as a legacy label inside that one design file.

For any Phase 2+ screen (wallets, transactions, budgets, insights, SMS suggestion card, etc.), treat this Claude Design project as the source of truth for the actual UI, not just the palette/type-scale summary in `DESIGN_BRIEF.md`.

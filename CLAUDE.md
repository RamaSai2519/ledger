# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

All of `plan.md`'s phased roadmap (§15, Phase 0 through Phase 7) is implemented and pushed to `master` — see Jira `LED-2` through `LED-9` (one issue per phase). A substantial amount of post-MVP work has landed on top: loans as a dedicated domain (`LED-14`), a fully layered/explainable SMS parser (`LED-18`), layered wallet/category SMS prefill with a learning loop (`LED-19`), mobile FCM integration + household-join preview + category drag-reorder (`LED-15`), several UI-fidelity and bugfix passes (`LED-10`, `LED-12`, `LED-16`, `LED-17`), and a backend route-input refactor (`LED-13`). Backend is deployed live on AWS Lambda — see the root [`README.md`](README.md) for the URL.

Per the Jira workflow below, most of these issues sit in **In Review** rather than **Done** — that's a process gate (only moved to Done once confirmed merged/deployed), not a signal the work is incomplete. Check an issue's own status/comments in Jira before assuming something is unbuilt; don't infer scope from this file's prose alone.

**One known, real gap**: the nightly balance-reconciliation safety net (plan.md §6) exists as a tested function (`services/api/src/jobs/balance_reconciliation.py`) but is **not wired to any scheduler** — it's absent from `infra/terraform/scheduler.tf` and from `index.py`'s `scheduled_handler` dispatch table, unlike every other job in `jobs/`. It only runs if invoked manually. Worth its own Jira issue if picked up.

**Known plan.md/reality drift** (implementation is correct; the spec text is stale):
- **Scheduled jobs run via AWS EventBridge Scheduler invoking the deployed Lambda's `scheduled_handler`**, not APScheduler/Celery as plan.md §3/§15 describes — see `docs/decisions/0005-eventbridge-scheduler-for-jobs.md` for why (a zip-deployed Lambda has no persistent process for an in-process scheduler to run in).
- **API base path is root, not `/api`** — plan.md §11 documents every route under `/api`, but the actual deployed API and `apps/mobile/src/api/client.ts`'s `API_BASE_URL` both use unprefixed paths (e.g. `/auth/login`, `/actions/health`), consistently with each other, just not with the written spec.
- **Loans are a dedicated `loans` collection**, not a `wallet` with `type=loan` — `LED-14` moved them out of the wallet model (EMI-driven amortization doesn't fit the wallet shape) and migrated the one pre-existing loan wallet. `loan` was fully removed from `CREATABLE_WALLET_TYPES`; plan.md §4's `wallets.loan_details` subdoc description is stale.
- **Mobile token storage uses `react-native-keychain`** (`apps/mobile/src/state/authStore.ts`), not `react-native-mmkv`/`expo-secure-store` as plan.md §3/§14 suggests — same encrypted-native-storage requirement, different library.

- `plan.md` — full backend + mobile implementation plan (data model, API reference, phased roadmap). Treat it as the original design intent, not a live source of truth for what's built — cross-check against Jira/the code for anything load-bearing, per the drift noted above.
- `DESIGN_BRIEF.md` — visual/UX design brief; the actual mockups it produced live in the Claude Design project linked under "Design reference" below, not as files in this repo

Backend: `cd services/api/src && pipenv install && pipenv run pytest -v`. Mobile: `cd apps/mobile && npm install && npm run typecheck`. See each directory's own README for the full command list and layout.

## What this project is

**Ledger** — a private household expense tracker for two people sharing one pooled ledger (no expense-splitting/settle-up). Each partner has a separate login but sees the exact same shared data. Android-only mobile app + Flask/MongoDB backend. The standout feature is background parsing of incoming bank SMS to auto-suggest transactions via push notification.

Full product/architecture detail lives in `plan.md`; read it before scaffolding the backend or mobile app. Key points to know going in:

### Tech stack (as built)
- **Backend:** Python 3.12/3.14 (see `services/api/Pipfile` for the pinned version), Flask + Flask-RESTful, PyMongo, Flask-JWT-Extended, shared `Input` dataclasses (`shared/interfaces.py`) for request validation, AWS EventBridge Scheduler dispatching into the same Lambda's `scheduled_handler` for background jobs (not APScheduler/Celery — see the drift note above), Firebase Admin SDK for FCM, MongoDB Atlas, zip-deployed to AWS Lambda behind API Gateway via Terraform (not Docker/Gunicorn/Nginx — see the deployment section below).
- **Mobile:** React Native (bare workflow — required for the custom native SMS module, not Expo-managed; `apps/mobile/android/` is a real generated native project), React Navigation, TanStack Query (server state) + Zustand (local UI state), a custom Kotlin `BroadcastReceiver` native module for SMS (`apps/mobile/android/.../sms/SmsReceiver.kt` + `SmsAllowlist.kt`, plus a debug-only `SmsExportReceiver.kt` for the LED-18 ADB dev pipeline), `@react-native-firebase/messaging`, `react-native-biometrics`, `react-native-keychain` for encrypted token storage, `react-native-svg`/`react-native-reanimated`/`react-native-gesture-handler`/`react-native-draggable-flatlist` for charts, wallet-card swipe, and category drag-reorder.

### Non-negotiable constraints (from plan.md §2)
1. **Play Store SMS policy**: general apps can't get broad `READ_SMS`/`RECEIVE_SMS` approval for public listing. Distribute via sideloaded APK or Play Console Internal Testing track only — never plan for open Play Store release while SMS reading exists.
2. **SMS parsing must be data-driven**, not hardcoded — bank message formats change without notice, so parser rules live in the `sms_parser_rules` MongoDB collection (editable without a release).
3. **Data minimization**: only forward SMS from a curated bank/sender allow-list (filtered client-side before it ever leaves the device); purge raw SMS text after ~30 days or resolution.
4. Use **MongoDB Atlas**, not self-hosted Mongo.

### Core domain model
All collections are scoped by `household_id` except `users`. See `plan.md` §4 for full field-level schemas of `users`, `households`, `wallets`, `categories`, `transactions`, `recurring_rules`, `budgets`, `notifications`, `sms_inbox`, `merchant_category_map`, `sms_parser_rules`, `net_worth_snapshots` — still accurate for those. Two collections plan.md §4 doesn't describe (added post-MVP): `loans` (`LED-14`, dedicated collection — see the drift note above, `loan` is no longer a wallet type) and `merchant_wallet_map` (`LED-19`, mirrors `merchant_category_map` but learns merchant → wallet instead of merchant → category, with a frequency>2 decay guard).

Things that are easy to get wrong if you don't read the plan first:
- **Balance sign convention**: for `bank_account`/`cash`, positive `current_balance` = asset. For `credit_card`/`pay_later`, positive = liability owed; `loans` (a separate collection, not a wallet type) contribute their own `outstanding_balance` to net-worth liabilities. Net worth = Σassets − Σliabilities.
- **`current_balance` is a cached field**, atomically maintained via `$inc` on every transaction write, wrapped in a Mongo multi-document transaction for transfers (two wallets touched at once). `jobs/balance_reconciliation.py` recomputes from `opening_balance` + transaction history and flags drift as a correctness safety net, but **is not currently wired to any scheduler** (see the known-gap note above) — don't assume it's actually running nightly in production without checking `scheduler.tf` first.
- **Manual reconcile never silently overwrites a balance** — it computes the delta and inserts an `adjustment`-type transaction against a system "Balance Adjustment" category, so the ledger stays internally consistent and auditable.
- **SMS pipeline dedup**: before creating a suggestion, check for an existing transaction on the same wallet with a similar amount within the same day (or a matching `transaction_id`/UTR, LED-18); if found, silently link `sms_id` to it instead of prompting again.
- **The "learning" mechanism** for SMS suggestions is layered, frequency-based matching (`LED-19`) — `merchant_category_map` (+ its `aliases` field for fuzzy merchant matching) for category, `merchant_wallet_map` for wallet, both incremented on accept, both falling back through cheaper heuristics (institution match, single-wallet-of-type, a household's `is_default` wallet, a small keyword-rule collection) when there's no learned mapping yet — no ML, intentionally. See `shared/sms_parsing.py`'s `resolve_wallet_layered`/`suggest_category_layered`.
- Net worth history is served from a **daily snapshot job** (`net_worth_snapshots`), not computed on the fly, since historical net worth requires replaying all transactions up to a date.

### API surface
**Base path is root, not `/api`** (see the drift note above) — routes are `/auth/...`, `/wallets/...`, `/sms/...` etc. directly, matching `apps/mobile/src/api/client.ts`. plan.md §11's route *table* (which endpoints exist, their methods/params) is otherwise still accurate; only its stated `/api` prefix is wrong. Loans (`/loans`, `LED-14`) and the SMS suggestion accept/dismiss/parser-rules routes (`LED-7`/`LED-18`/`LED-19`) aren't in plan.md §11 at all — check `services/api/src/services/controller.py` for the current full route list.

### Build order
plan.md §15's phased roadmap (Setup → Auth & Household → Core Ledger → Budgets & Notifications → Insights → SMS Pipeline → Recurring Transactions → Polish & Ship) is now historical — all phases are built (Jira `LED-2` through `LED-9`). It's still useful as a dependency map if you're ever rebuilding a phase from scratch (later phases assume earlier ones' foundations), but isn't a to-do list any more.

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

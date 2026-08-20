# Khaata — Household Expense Tracker
## Full Implementation Plan (Backend + Mobile)

Working name: **Khaata** (placeholder, change freely) — resolved: the product is now named **Ledger** everywhere (repo `RamaSai2519/ledger`, AWS resources, Jira project `LED`). Two-user household expense tracker with SMS-based transaction detection, Android-only, Flask + MongoDB backend.

**High-fidelity mockups:** a Claude Design project has the actual screens for every phase below — `https://claude.ai/design/p/4e2b7218-8fbc-41c1-af26-2058b55579b2?file=Khaata+App.dc.html`. Read it via the `claude_design` MCP (auth via `/design-login`) before implementing any screen; `Khaata App.dc.html` is the file with the designs, importing `android-frame.jsx` (device-frame chrome) and `support.js` (canvas runtime, not design content). The project still says "Khaata" — treat that as the design file's legacy label, not the product name.

---

## 1. Product Summary

- Two people ("household") each have **fully separate logins** (mobile number + password) but **shared, unrestricted visibility** into all wallets, transactions, categories, and budgets. No expense-splitting or settle-up math — it's one pooled ledger, viewed from two accounts.
- Multiple **wallets**: bank accounts, credit cards, pay-later (BNPL) accounts, cash, loans.
- **Customizable categories** (flat list, expense + income).
- **Manual transaction entry** and **manual balance reconciliation**.
- **SMS-based auto-detection**: Android app forwards relevant transactional SMS to the backend, which parses it, suggests a category/wallet, and pushes a notification to confirm/edit/dismiss.
- **Budgets** (per category, per wallet, and overall) with both threshold-based and digest-based notifications.
- **Insights**: daily/monthly/yearly trends, income vs. expense, and net-worth-over-time.
- **App lock**: PIN + biometric, on top of server-side auth.

---

## 2. Critical Constraints — Read First

These affect architecture decisions below, so flagging them up front:

1. **Google Play SMS permission policy.** Play Store restricts `READ_SMS`/`RECEIVE_SMS` to a small set of approved use cases (default SMS handler, etc.) — a general expense tracker does **not** qualify for public Play Store distribution with broad SMS access. Since this is a 2-person personal app, plan to distribute via:
   - A directly-installed release APK (sideload) on both phones, **or**
   - Google Play Console's **Internal Testing** track (up to 100 testers, relaxed sensitive-permission review), which is the more maintainable option since it still gives you auto-update infrastructure.
   Do **not** plan for open/production Play Store listing while this feature exists, unless you later drop to notification-based detection instead of SMS.
2. **Bank SMS formats change over time without notice.** Parsing must be data-driven (rules stored in MongoDB, not hardcoded regex in app/server code) so you can fix a broken parser by editing a database row, not shipping a release.
3. **Sensitive data minimization.** Raw SMS text will pass through your backend. Store it only as long as needed to resolve a suggestion (e.g., purge raw text after 30 days or after confirmation), and only forward SMS from a curated allow-list of known bank/transactional sender IDs from the client — never all SMS.
4. **MongoDB Atlas** (managed) is recommended over self-hosting Mongo — encryption at rest, automated backups, and low ops burden matter more than cost for financial data at this scale.

---

## 3. Tech Stack

**Backend**
- Python 3.12, Flask, Blueprints for modular routes
- PyMongo (or Flask-PyMongo) for MongoDB access
- Flask-JWT-Extended for auth (access + refresh tokens)
- Pydantic or Marshmallow for request/response validation
- APScheduler for MVP scheduled jobs (budget digests, net-worth snapshots, bill-due reminders) → migrate to Celery + Redis or AWS EventBridge + Lambda if/when it needs to scale
- Firebase Admin SDK for push notifications (FCM)
- Gunicorn + Nginx, Dockerized
- MongoDB Atlas (M0/M2 tier is plenty for 2 users)
- Deploy target: AWS (ECS Fargate or a single EC2 + Docker Compose — EC2 is simplest given a 2-user app), Secrets Manager for credentials, CloudWatch for logs
- GitHub Actions for CI/CD (build, test, deploy on merge to main)

**Mobile (Android only)**
- React Native (bare workflow, not Expo-managed, since a custom native module is needed for SMS listening)
- React Navigation (stack + bottom tabs)
- TanStack Query for server state/caching, Zustand for local UI state
- A custom native Kotlin module wrapping a `BroadcastReceiver` on `SMS_RECEIVED_ACTION`, filtered client-side to an allow-list of bank sender IDs before ever touching JS/network (do **not** rely on unmaintained community SMS packages for this — write a small dedicated module)
- `@react-native-firebase/messaging` for push notifications
- `react-native-biometrics` (or `expo-local-authentication` if you end up on Expo dev-client) for biometric app lock
- `react-native-mmkv` or `expo-secure-store` for encrypted local token/PIN storage
- Charting: `react-native-gifted-charts` or `victory-native` (needs to support gradient-filled area/line charts per the design reference)

---

## 4. Data Model (MongoDB Collections)

All collections below are scoped by `household_id` except `users`. Use ObjectIds for `_id` unless noted.

### `users`
| Field | Type | Notes |
|---|---|---|
| mobile_number | string, unique, indexed | login identifier |
| password_hash | string | bcrypt/argon2 |
| name | string | |
| household_id | ObjectId | ref → households |
| pin_hash | string | local app-lock PIN, hashed |
| fcm_tokens | array[string] | multi-device support |
| created_at / updated_at | datetime | |

### `households`
| Field | Type | Notes |
|---|---|---|
| name | string | e.g. "Rama & Partner" |
| member_ids | array[ObjectId] | max 2 for this product |
| invite_code | string, indexed | 6-char alphanumeric, regenerable |
| created_at | datetime | |

**Household join flow:** first user to sign up creates a household and becomes owner, receiving an invite code (visible any time in Settings). Second user either enters the code during signup or joins later from Settings → "Join household." Once `member_ids.length == 2`, lock further joins.

### `wallets`
| Field | Type | Notes |
|---|---|---|
| household_id | ObjectId | |
| name | string | e.g. "HDFC Savings" |
| type | enum | `bank_account`, `credit_card`, `pay_later`, `cash`, `loan` |
| provider | string | bank/institution name — used to match SMS sender |
| account_last4 | string, optional | for disambiguating multiple wallets from same bank |
| opening_balance | decimal | baseline |
| current_balance | decimal (cached) | atomically updated on every transaction; see §6 |
| currency | string | fixed `INR` |
| icon / color | string | UI |
| is_archived | bool | |
| credit_card_details | subdoc, if type=credit_card | `{credit_limit, statement_day, due_day, min_due_percent}` |
| pay_later_details | subdoc, if type=pay_later | `{credit_limit, billing_cycle_day, due_day}` |
| loan_details | subdoc, if type=loan | `{principal, interest_rate, tenure_months, emi_amount, start_date}` |
| created_by | ObjectId | user who added it |
| created_at / updated_at | datetime | |

**Balance sign convention:** for `bank_account`/`cash`, positive `current_balance` = money held (asset). For `credit_card`/`pay_later`/`loan`, positive `current_balance` = amount owed (liability). Net worth = Σ(assets) − Σ(liabilities).

### `categories`
| Field | Type | Notes |
|---|---|---|
| household_id | ObjectId | |
| name | string | |
| type | enum | `expense`, `income` |
| icon / color | string | |
| is_default | bool | seeded categories, see §12 |
| is_archived | bool | |
| sort_order | int | per-household display order; user-reorderable via `PATCH /categories/reorder` (LED-15) |

### `transactions`
| Field | Type | Notes |
|---|---|---|
| household_id | ObjectId | |
| wallet_id | ObjectId | |
| category_id | ObjectId, nullable for transfers | |
| user_id | ObjectId | who logged it (attribution only, not access control) |
| type | enum | `expense`, `income`, `transfer`, `adjustment` |
| amount | decimal | always positive; sign implied by type |
| transfer_to_wallet_id | ObjectId, only if type=transfer | |
| merchant_name | string, optional | |
| note | string, optional | |
| date | date | transaction date (may differ from created_at) |
| source | enum | `manual`, `sms_confirmed` |
| sms_id | ObjectId, optional | ref → sms_inbox, for audit/dedup |
| recurring_rule_id | ObjectId, optional | |
| created_at / updated_at | datetime | |

### `recurring_rules`
| Field | Type | Notes |
|---|---|---|
| household_id, wallet_id, category_id | ObjectId | |
| merchant_name | string | |
| amount | decimal, nullable | null if amount varies cycle to cycle |
| frequency | enum | `weekly`, `monthly`, `yearly` |
| next_due_date | date | |
| auto_detected | bool | false in MVP (manual only); true reserved for V2 |
| is_active | bool | |

### `budgets`
| Field | Type | Notes |
|---|---|---|
| household_id | ObjectId | |
| scope | enum | `category`, `wallet`, `overall` |
| scope_ref_id | ObjectId, nullable | category_id or wallet_id; null if overall |
| amount | decimal | monthly cap |
| period | enum | `monthly` (only option in MVP) |
| threshold_percents | array[int] | default `[80, 100]`, configurable |
| created_at | datetime | |

### `notifications` (in-app log, mirrors what's pushed via FCM)
| Field | Type | Notes |
|---|---|---|
| household_id, user_id | ObjectId | target |
| type | enum | `budget_threshold`, `budget_exceeded`, `sms_suggestion`, `digest`, `bill_due` |
| payload | object | type-specific data |
| is_read | bool | |
| created_at | datetime | |

### `sms_inbox` (staging area for parsed SMS)
| Field | Type | Notes |
|---|---|---|
| household_id, user_id | ObjectId | user_id = whose phone received it |
| raw_text | string | purge after resolution window (see §2.3) |
| sender_id | string | e.g. `HDFCBK` |
| received_at | datetime | |
| parse_status | enum | `pending`, `parsed`, `ignored`, `failed`, `not_transaction` (LED-18: recognized as OTP/promotional/balance-only/statement/due-reminder/other — distinct from `failed`, which means transactional wording matched but no amount could be extracted) |
| parsed_amount, parsed_direction (debit/credit), parsed_last4, parsed_merchant, parsed_ref | — | extracted fields |
| transaction_type | enum, LED-18 | full type (`upi_payment`, `imps`, `refund`, `emi_payment`, `salary`, ... — see `shared/sms/types.py::TransactionType`), separate from the coarser `parsed_direction` |
| transaction_status | enum, LED-18 | `success`/`pending`/`failed`/`reversed`/`refunded` |
| merchant_normalized, counterparty, payment_method, balance_after | — | LED-18: alias-normalized merchant name, P2P counterparty (mutually exclusive with merchant), detected UPI/wallet app, balance-after-transaction |
| field_confidences, parse_evidence | object, array[string] | LED-18: per-field confidence + human-readable reasoning trail (spec Part 13 "explainable confidence"), not just the single `confidence_score` |
| suggested_wallet_id, suggested_category_id, confidence_score | — | |
| status | enum | `suggested`, `accepted`, `dismissed`, `not_applicable` (LED-18: set for `not_transaction` parse_status and for transactional-but-not-completed states — reversed/failed/pending — so they never surface via `/sms/suggestions` or a push) |
| resolved_transaction_id | ObjectId, optional | |

### `merchant_aliases` (LED-18, merchant canonicalization)
| Field | Type | Notes |
|---|---|---|
| raw_key | string | `normalize_key()`'d raw merchant string variant, unique |
| raw_variant | string | the original (un-normalized) variant, for reference |
| canonical_name | string | display name every variant maps to |

### `merchant_category_map` (the "learning" layer)
| Field | Type | Notes |
|---|---|---|
| household_id | ObjectId | |
| merchant_pattern | string | normalized merchant string |
| category_id | ObjectId | |
| wallet_id | ObjectId, optional | if merchant reliably maps to one wallet |
| frequency | int | incremented every time confirmed |
| last_used_at | datetime | |

### `sms_parser_rules` (data-driven, extensible — this is what makes bank support "customizable")
| Field | Type | Notes |
|---|---|---|
| bank_code | string | e.g. `HDFC`, `AXIS`, `KOTAK`, `SBI`, `ZET`, `AXIO`, `JUPITER`, `CANARA` |
| sender_ids | array[string] | known SMS sender IDs for this bank |
| institution_name, aliases, keywords | string, array[string], array[string] | LED-18: weighted evidence for `InstitutionResolver` (sender match / body name match / keyword match) — see `shared/sms/institution_resolver.py` |
| patterns | array[object] | `{txn_type: debit/credit, regex, field_groups: {amount, last4, merchant, ref}}` — legacy per-bank extraction patterns, still stored/listable via `POST /sms/parser-rules` but no longer executed by the LED-18 pipeline, which extracts generically instead (see `services/api/docs/sms_parser.md`) |
| is_active | bool | |
| household_id | ObjectId, nullable | null = global/default rule; set = household-specific custom rule |

Seed this collection at launch with rules for **Axis, HDFC, Kotak, SBI, Zet Credit Card, Amazon Pay Later (Axio), Jupiter Credit Card, and Canara**, plus one generic fallback pattern that just extracts an amount + debit/credit keyword for unrecognized senders (flagged low-confidence, always asks user to pick wallet/category manually).

### `net_worth_snapshots` (for the net-worth-over-time chart)
| Field | Type | Notes |
|---|---|---|
| household_id | ObjectId | |
| date | date | one per day |
| total_assets, total_liabilities, net_worth | decimal | |
| per_wallet_breakdown | object | wallet_id → balance |

Populated by a nightly scheduled job — needed because computing historical net worth on-the-fly for an arbitrary past date means replaying all transactions, which doesn't scale well for chart rendering; a daily snapshot is cheap to query.

---

## 5. Auth & Household Flow

1. **Sign up:** mobile number, password, name → creates `users` doc. Then choose: "Create household" (generates invite code) or "Join household" (enters partner's code).
2. **Log in:** mobile + password → JWT access token (~15 min) + refresh token (~30 days, stored in encrypted device storage).
3. **Password hashing:** bcrypt or argon2, never plaintext, never logged.
4. **Rate limiting:** lock out after N failed login attempts (e.g. 5) for a cooldown window — financial app, worth the extra guard even at 2-user scale.
5. **App lock (client-side, separate from server auth):** on app foreground/launch, require PIN or biometric before rendering any data. PIN hash stored locally (Android Keystore-backed secure storage), not necessarily synced to backend unless you want cross-device PIN recovery (optional, skip for MVP — just offer "reset via password login" if PIN is forgotten).

---

## 6. Wallets & Balance Engine

- `current_balance` is a **cached, atomically maintained field** — every transaction create/update/delete adjusts it via MongoDB `$inc` inside the same request (wrap multi-document changes, e.g. transfers touching two wallets, in a Mongo multi-document transaction using a session).
- Run a **nightly reconciliation job** that recomputes each wallet's balance from `opening_balance` + all transactions, and flags (logs / alerts) any drift from the cached value — a correctness safety net.
- **Manual reconcile flow:** user enters the real-world balance from their bank/card statement. Backend computes the delta vs. `current_balance` and creates an `adjustment`-type transaction (category auto-set to a system "Balance Adjustment" category) so the ledger and net-worth history stay internally consistent — never silently overwrite the balance without a paper trail.
- **Transfers** (e.g., paying off a credit card from a bank account) create a linked pair via `type=transfer` + `transfer_to_wallet_id`, decrementing the source and incrementing/reducing-liability on the destination in one transaction.

---

## 7. SMS Parsing Pipeline (end to end)

1. On first SMS-dependent action, Android app shows a **permission rationale screen** (why SMS access is needed, what is/isn't sent) before requesting `RECEIVE_SMS`/`READ_SMS`.
2. A native `BroadcastReceiver` listens for incoming SMS. **Client-side filter first:** only SMS from a bundled allow-list of known bank/transactional sender IDs are ever forwarded — personal SMS never leaves the device.
3. Matching SMS → `POST /api/sms/ingest` with `{raw_text, sender_id, received_at}`. Queued locally and retried if offline (simple local queue is enough; full offline support isn't otherwise a priority per scope).
4. Backend matches `sender_id` against `sms_parser_rules`, applies the matching regex pattern to extract amount, debit/credit direction, last-4, merchant name, reference number.
5. Backend attempts to resolve which `wallet` this belongs to (match on `provider` + `account_last4`); if ambiguous or no match, mark low-confidence and let the user pick on confirm.
6. Backend queries `merchant_category_map` for a category suggestion (normalized merchant string lookup, most-frequent match wins); computes a confidence score.
7. Creates an `sms_inbox` record (`status=suggested`), sends an **FCM push notification**: e.g. "₹450 at Swiggy — HDFC Card. Add as Food expense?" with Confirm / Edit / Dismiss actions deep-linking into the app.
8. **Confirm** → creates the `transaction` (`source=sms_confirmed`), updates wallet balance, increments `merchant_category_map.frequency`.
9. **Edit + confirm** → same, but the corrected category/wallet is written back to `merchant_category_map`, improving future suggestions for that merchant (this is the whole "learning" mechanism — simple frequency-based matching is enough to start; no ML needed for two users).
10. **Dismiss** → `sms_inbox.status=dismissed`, no transaction created.
11. **Dedup:** before creating a suggestion, check for an existing transaction with the same wallet + similar amount within a small time window (e.g. ±same day) to avoid double-prompting if the user already logged it manually. If a match is found, silently link `sms_id` to the existing transaction instead of creating a new suggestion.
12. **Manual entry always available** regardless of SMS status — SMS is a convenience layer, never a blocker.

---

## 8. Budgets & Notifications

- Budgets can be set at **category**, **wallet**, or **overall (household-wide monthly cap)** level — all three scopes supported simultaneously.
- Progress = sum of `expense` transactions in the current calendar month matching the budget's scope.
- Notifications fire on:
  - **Threshold crossing** — configurable percentages (default 80% and 100%) per budget.
  - **Digest** — a daily or weekly summary notification (spend so far, top category, days left in budget period) regardless of threshold status.
- Also use this notification pipeline for **credit card / loan due-date reminders**, since you're tracking full credit card details (statement/due dates) — a scheduled job checks upcoming `due_day` fields a few days ahead and fires a `bill_due` notification.

---

## 9. Insights

- **Trend chart** (daily / monthly / yearly toggle): total expense (and optionally income) over the selected period, area/line chart.
- **Income vs. expense**: comparison view per period (bar or dual-line).
- **Net worth over time**: reads from `net_worth_snapshots`, shows assets − liabilities trending over months.
- **Category breakdown**: spend by category for the selected period (bar or pie).

---

## 10. Recurring Transactions

- MVP: **manual only** — user creates a `recurring_rule` (merchant, amount or "varies", frequency, wallet, category). A scheduled job checks `next_due_date` and either auto-creates the transaction or sends a reminder to confirm it (configurable per rule), then advances `next_due_date`.
- V2 (future): auto-detect recurring patterns from confirmed SMS transactions (same merchant + similar amount + regular interval) and suggest turning them into a `recurring_rule` — flagged as `auto_detected=true`.

---

## 11. API Reference

Base path: `/api`

**Auth**
| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/signup` | mobile, password, name |
| POST | `/auth/login` | mobile, password → tokens |
| POST | `/auth/refresh` | refresh → new access token |
| POST | `/auth/logout` | invalidate refresh token |
| POST | `/auth/household/create` | creates household, returns invite code |
| POST | `/auth/household/join` | body: invite_code |
| GET | `/auth/household/invite-code` | fetch current code |
| POST | `/auth/pin` | set/update local PIN hash server-side backup (optional) |

**Users**
| GET | `/users/me` | profile |
| PATCH | `/users/me` | update name etc. |
| POST | `/users/fcm-token` | register device token |

**Wallets**
| GET | `/wallets` | list (household-scoped) |
| POST | `/wallets` | create |
| GET/PATCH/DELETE | `/wallets/:id` | detail / update / archive |
| POST | `/wallets/:id/reconcile` | body: actual_balance → creates adjustment txn |
| GET | `/wallets/:id/balance-history` | for wallet-level chart |

**Categories**
| GET | `/categories` | list |
| POST | `/categories` | create |
| PATCH/DELETE | `/categories/:id` | update / archive |

**Transactions**
| GET | `/transactions` | filters: wallet_id, category_id, date_range, type, user_id, pagination |
| POST | `/transactions` | create |
| GET/PATCH/DELETE | `/transactions/:id` | |
| POST | `/transactions/transfer` | wallet-to-wallet |

**Recurring**
| GET/POST | `/recurring` | |
| PATCH/DELETE | `/recurring/:id` | |
| POST | `/recurring/:id/skip-next` | |

**Budgets**
| GET/POST | `/budgets` | |
| PATCH/DELETE | `/budgets/:id` | |
| GET | `/budgets/:id/progress` | |

**Insights**
| GET | `/insights/trends?period=daily\|monthly\|yearly&from=&to=` | |
| GET | `/insights/income-vs-expense?period=` | |
| GET | `/insights/net-worth-history?from=&to=` | |
| GET | `/insights/category-breakdown?period=` | |

**SMS**
| POST | `/sms/ingest` | body: raw_text, sender_id, received_at |
| GET | `/sms/suggestions` | pending suggestions |
| POST | `/sms/suggestions/:id/accept` | optional overrides: category_id, wallet_id, amount |
| POST | `/sms/suggestions/:id/dismiss` | |
| GET/POST | `/sms/parser-rules` | manage custom bank parsers (V2 UI, but build the endpoint in MVP so it's ready) |

**Notifications**
| GET | `/notifications` | |
| POST | `/notifications/:id/read` | |

---

## 12. Default Seed Data

**Expense categories:** Food & Dining, Groceries, Transport, Fuel, Shopping, Bills & Utilities, Rent, EMI / Loan Payment, Entertainment, Health & Fitness, Subscriptions, Travel, Education, Personal Care, Gifts & Donations, Balance Adjustment (system, hidden from manual picker), Miscellaneous.

**Income categories:** Salary, Freelance / Business, Investment Returns, Refunds / Cashback, Other Income.

Seed these per household on creation, `is_default=true`, editable/archivable but not hard-deletable if referenced by existing transactions.

---

## 13. Mobile App Structure

**Navigation:** bottom tab bar with a center floating action button for "Add Transaction" (matches the visual reference) — suggested tabs: **Home, Wallets, [+], Insights, Settings**. Budgets live inside Home (summary widget) and a dedicated section under Insights or Settings.

**Screens:** Splash → Onboarding (optional) → Sign Up / Log In → Household Create-or-Join → SMS Permission Rationale → PIN Setup → App Lock (recurring, on each open) → Home/Dashboard → Wallets List → Wallet Detail → Add/Edit Wallet → Add/Edit Transaction → Categories Management → Budgets → Insights (Trends / Income-vs-Expense / Net Worth tabs) → SMS Suggestion confirm sheet → Notifications Inbox → Settings (profile, household/invite code, categories, wallets, PIN/biometric toggle, logout).

**State management:** TanStack Query for all server data (auto-caching, refetch-on-focus fits a shared-household model where the partner's device may add data at any time); Zustand for local-only UI state (active tab, form drafts).

**Key native concern:** the SMS `BroadcastReceiver` needs to keep working even when the app is backgrounded/killed — implement it as a proper native Android component registered in the manifest (not a JS-only listener that dies with the RN bridge), forwarding matched SMS to a background fetch/headless JS task or directly making the network call natively.

---

## 14. Security & Privacy Checklist

- HTTPS/TLS everywhere (API, FCM).
- Passwords: bcrypt/argon2 hashed, never logged.
- JWT access tokens short-lived; refresh tokens stored in Android Keystore-backed secure storage, not plain AsyncStorage.
- Raw SMS text purged from `sms_inbox` after a resolution window (e.g. 30 days) — keep only the extracted structured fields for audit history.
- SMS forwarding is allow-list-based (known bank sender IDs only), enforced client-side before any network call.
- Login rate-limiting / lockout after repeated failures.
- MongoDB Atlas encryption at rest + IP allow-listing / VPC peering for the backend.
- No third-party analytics SDKs touching financial data without explicit thought — this is a private 2-person app, keep the attack surface small.

---

## 15. Phased Build Roadmap

1. **Phase 0 — Setup:** repo structure (backend + mobile in one monorepo or two repos, your call), Flask skeleton, MongoDB Atlas cluster, Docker, GitHub Actions CI, RN project scaffold, Firebase project.
2. **Phase 1 — Auth & Household:** signup/login, JWT, household create/join, PIN + biometric app lock.
3. **Phase 2 — Core Ledger:** wallets CRUD (all 5 types), categories CRUD + seed, manual transactions CRUD, balance engine (§6), reconcile flow.
4. **Phase 3 — Budgets & Notifications:** budget CRUD + progress calc, FCM wiring, threshold + digest jobs, bill-due reminders.
5. **Phase 4 — Insights:** trend/income-vs-expense/net-worth endpoints, nightly snapshot job, frontend charts.
6. **Phase 5 — SMS Pipeline:** Android permission flow + native BroadcastReceiver, ingest endpoint, seed `sms_parser_rules` for the 8 target banks, suggestion generation + push, confirm/edit/dismiss UI, merchant learning map, dedup logic.
7. **Phase 6 — Recurring Transactions:** manual rules + reminder job.
8. **Phase 7 — Polish & Ship:** settings screen, empty/error/loading states across the app, QA pass on SMS parsing against real sample messages from each of the 8 banks, release APK build, distribute via Internal Testing track or direct sideload.

---

## 16. Future Enhancements (explicitly out of scope for MVP, noted for later)

- Auto-detected recurring transactions from SMS patterns.
- Notification-listener-based detection (UPI app notifications) as a supplement to SMS.
- Data export (CSV/PDF).
- Offline-first sync beyond the basic SMS ingest queue.
- Photo/receipt attachments on transactions.
- Expense-splitting/settle-up math, if the "pure joint ledger" model ever needs to change.
- In-app UI for managing custom `sms_parser_rules` (endpoint is planned from MVP; UI can wait).

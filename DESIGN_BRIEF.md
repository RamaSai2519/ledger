# Design Brief: Khaata — Household Expense Tracker (Android, Dark Theme)

This is a prompt for a design agent to produce high-fidelity mobile UI mockups. No code implementation is expected from this pass — just the visual design system and screens.

---

## 1. Product Context

**What it is:** A private expense tracker for a couple living together (working name: **"Khaata"** — placeholder, feel free to typeset it as the app name unless told otherwise). Each partner logs in separately, but both see the exact same shared ledger — every wallet, transaction, category, and budget is fully visible to both. There is no expense-splitting or "who owes whom" — it's one pooled household ledger viewed from two accounts.

**Platform:** Android only, single primary device size to design for (~390×844dp, standard modern Android phone). Portrait only.

**Standout feature:** The app reads incoming bank SMS in the background and surfaces a confirm/edit/dismiss prompt to add the detected transaction — this "SMS suggestion" moment (delivered as a push notification and an in-app card) is a core, distinctive interaction and deserves real design attention, not just a generic dialog.

**Tone:** This is a private financial tool between two people, not a consumer social app. It should feel calm, precise, and trustworthy — closer to a well-made banking app than a budgeting-gamification app. No streaks, no badges, no forced positivity about spending.

---

## 2. Visual Reference

Two references, both dark-themed neo-banking UI:

**Reference A** (`https://cdn.dribbble.com/userupload/4152808/file/original-8c61bff7dfa67cccc7ee0663b67c4803.png`): A near-black balance screen with a large indigo/blue hero card showing a currency flag chip, balance figure, and three pill-shaped quick actions (Deposit / Withdraw / Transfer) below it in dark, white, and mint-green respectively. Below that, a transaction list with square app-icon avatars, merchant name + subtitle, amount, and a small percentage-change indicator. A second screen shows an "Insight" view: a large total-expense figure, a segmented Daily/Monthly/Yearly control, a smooth gradient-filled line chart with a floating value tooltip, and a horizontally-scrolling "Recent Uses" card row with toggle switches.

**Reference B** (`https://cdn.dribbble.com/userupload/32326640/file/original-51eda588bf638b54f9e37f3a28174b44.jpg`): A 3-screen flow — an onboarding screen with overlapping stacked "card" illustrations (a subscription card and an expense card, angled, sitting in front of a bold geometric shape) and a large headline + pill CTA button; a dashboard with a dual-line income/expense chart (green up, red/pink down) and a floating value callout; and a "My Wallets" screen showing 3 wallet cards side by side (bank, Visa card, crypto), each with a masked account number, followed by a bottom sheet with Transactions/Analytics tabs and a transaction list. Bottom navigation across all screens uses 4 icons plus a circular black center FAB.

**What to take from these:** the near-black base with a saturated indigo hero color, the pill-shaped multi-action row, the gradient area chart with a floating tooltip, the stacked/masked wallet card treatment, and the bottom nav + center FAB pattern. Treat these as a strong starting point, not a template to trace exactly — see §4 on making it distinctive.

---

## 3. Full Screen List

Design all of the following (states noted where relevant):

1. **Splash screen**
2. **Onboarding** (1–2 screens introducing the shared-ledger + auto-detect concept — optional but nice to have, similar spirit to Reference B's intro screen)
3. **Sign up** (mobile number, password, name)
4. **Log in** (mobile number, password)
5. **Household setup** — two paths: "Create a household" (shows generated invite code to share) vs. "Join a household" (enter partner's code)
6. **SMS permission rationale** — a one-screen explainer shown before the Android permission prompt, plain-language about what is/isn't read
7. **PIN setup** + biometric enable toggle
8. **App lock screen** (PIN pad + biometric prompt) — shown every time the app opens
9. **Home / Dashboard** — hero card showing total net worth (assets − liabilities across all wallets), quick actions (Add Expense / Add Income / Transfer), recent transactions, a compact budget-status widget, upcoming bill/due-date reminders
10. **Wallets list** — grouped or tabbed by type (bank, credit card, pay-later, cash, loan), masked account numbers, balance per wallet, clear visual distinction between "money you have" and "money you owe"
11. **Wallet detail** — single wallet's transaction history, mini balance-history chart, "Reconcile balance" action, edit/archive
12. **Add / edit wallet form** — type selector with conditional fields (credit card: limit + statement/due date; loan: principal + EMI + tenure)
13. **Add / edit transaction** — amount entry, wallet picker, category picker (icon grid), date, note, expense/income/transfer toggle, "mark as recurring" toggle. Include the numeric keypad state.
14. **Categories management** — expense/income tabs, icon + color per category, add/edit/archive
15. **Budgets** — list of active budgets (category / wallet / overall) with progress indicators, add-budget form with threshold sliders
16. **Insights** — segmented Daily/Monthly/Yearly control, trend area chart, income-vs-expense comparison, net-worth-over-time chart, category breakdown
17. **SMS suggestion card** — this is the signature interaction (see §4). Shown as a bottom sheet or full card: parsed merchant, amount, guessed wallet + category (editable inline), Confirm / Edit / Dismiss actions. Design both the push notification's expanded state and the in-app equivalent.
18. **Notifications inbox** — list of past alerts (budget threshold, bill due, SMS suggestions resolved/pending), read/unread treatment
19. **Settings** — profile, household members + invite code (sharing UI), manage categories, manage wallets, PIN/biometric toggle, log out

For at least Home, Wallets, Add Transaction, and Insights, also design: **empty state** (no data yet), **loading state**, and **error state** (e.g. failed to load). Empty states should read as an invitation to act, not a dead end — e.g. "No wallets yet — add your first bank account or card" with the CTA right there, not a generic illustration with no next step.

---

## 4. Design Direction

Work in two passes, per your usual process: first a compact token system (below is a starting point, not a mandate — refine it), then screens.

**Starting palette** (treat as a base to sharpen, not a locked spec):
- Background base: `#0B0B12` (near-black, slightly blue rather than pure neutral black)
- Surface / card: `#16161F`
- Hero / primary accent (indigo-blue, from both references): `#5B54F9`
- Positive / income accent: `#2FD988`
- Negative / expense-alert accent: `#FF6B6B`
- Text primary: `#F5F5F8`
- Text secondary / muted: `#8A8A94`
- Border / divider (subtle, on near-black): `#232330`

**Typography:** three roles —
- **Display** (large balance figures, hero numbers): something with a bit of geometric character, not a default system sans — used with restraint (headline numbers and screen titles only).
- **Body** (everything else — lists, labels, buttons): clean, highly legible neutral sans.
- **Utility / tabular** (all monetary figures in lists, tables, and charts): a face with proper **tabular figures** so amounts align vertically in lists — this matters more here than in most apps, given how many balance/amount columns this UI has. A monospaced or tabular-figure-enabled face is worth using specifically for numerals.

**Signature element — make this the one memorable thing:** Since the core subject here is a shared two-person ledger (not a solo finance app), consider a subtle dual-identity system: assign each partner a distinct accent hue (e.g., the indigo above for one, a warm contrasting amber/gold for the other), expressed as a thin colored edge, small avatar ring, or tag on transaction rows and dashboard activity to show who logged what — quiet, functional, not gamified or social-feed-like. This is specific to what this product actually is (a couple's joint book), so it's a good candidate for the "one real risk" — everything else around it should stay disciplined and quiet.

Also worth leaning into as a secondary motif (from Reference B): the **stacked, angled wallet-card illustration** for bank/credit/pay-later/cash/loan wallet types — masked numbers, type-specific iconography, subtle card-material shading — reused consistently across the wallets list, wallet detail, and add-transaction wallet-picker.

**Charts:** gradient-filled area/line charts with a floating value tooltip on scrub/hover (per Reference A's Insight screen) for trends and net worth; a clear two-color (green/red) comparison treatment for income vs. expense (per Reference B's dashboard).

**Avoid defaulting to:** a generic near-black-background-plus-single-neon-accent look with no other point of view — the palette above gives you a direction, but push it somewhere specific to this product (the dual-identity accent idea above is one way to do that) rather than leaving it as "dark fintech app #4712."

---

## 5. Copy & Microcopy Guidance

- Plain, active voice: "Add expense," not "Submit transaction." Buttons and their resulting confirmations should share vocabulary (a button that says "Save wallet" should be followed by a toast that says "Wallet saved," not "Success").
- Name things the way a person thinks about them, not the way the system is built — "Balance" not "Cached balance," "Add expense" not "Create transaction record."
- SMS suggestion copy should be concrete and specific: "₹450 at Swiggy, HDFC Card — add as Food expense?" not "New transaction detected."
- Error and empty states explain what happened and what to do next, in the interface's voice — no apologizing, no vagueness.

---

## 6. Deliverable Expectations

- High-fidelity screens for all items in §3, dark theme throughout, consistent component system (buttons, cards, list rows, chart components, bottom nav + FAB, bottom sheets, form inputs, numeric keypad).
- A short component/token summary alongside the screens (final palette, type scale, spacing scale, corner-radius scale, icon style) so a coding agent can implement it faithfully without guessing values.
- Empty / loading / error states for the four screens noted in §3.
- Keep interaction/motion notes lightweight — where a transition or micro-interaction matters (e.g. the SMS suggestion card appearing, chart scrub tooltip), a one-line note is enough; this doesn't need a full animation spec.

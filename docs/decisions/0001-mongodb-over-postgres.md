# ADR 0001: MongoDB over Postgres

**Status:** Accepted

## Context

`IMPLEMENTATION_PLAN.md` specifies MongoDB Atlas as the datastore. The data
model (wallets, transactions, categories, budgets, SMS staging, merchant
learning map) is document-shaped and mostly household-scoped rather than
deeply relational, and the household+wallet+category+transaction graph is
shallow enough that referential integrity can be enforced at the application
layer (validate parent ids exist before insert) rather than needing SQL
foreign keys.

## Decision

Use MongoDB Atlas (managed), not self-hosted Mongo and not Postgres.
Collections and fields are as specified in `IMPLEMENTATION_PLAN.md` §4.

## Consequences

- Every write path must validate parent ids (`household_id`, `wallet_id`,
  `category_id`) exist before inserting — no database-enforced foreign keys.
- `current_balance` on `wallets` is a cached, atomically-`$inc`ed field with
  a nightly reconciliation job as a correctness safety net (§6).

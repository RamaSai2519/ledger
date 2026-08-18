# Ledger

A private household expense tracker for two people sharing one pooled
ledger. See [`DESIGN_BRIEF.md`](DESIGN_BRIEF.md) for the product/visual
brief and [`plan.md`](plan.md) for the full
backend + mobile architecture and phased roadmap. [`CLAUDE.md`](CLAUDE.md)
has operating conventions (Jira, deployment, testing) for anyone (human or
agent) working in this repo.

## Status

Phase 0 (scaffold) and Phase 1 (auth & household) are built, tested, and
**deployed live**: https://w7ychchtd1.execute-api.ap-south-1.amazonaws.com
(Lambda `ledger-api` + HTTP API Gateway, `ap-south-1`, backed by a real
MongoDB Atlas cluster). Phases 2-7 (core ledger, budgets, insights, SMS
pipeline, recurring transactions, polish) are tracked as Jira backlog, not
yet built — see `plan.md` §15.

## Layout

```
apps/mobile/       React Native (bare) app
services/api/       Flask + Flask-RESTful backend, zip-deployed Lambda
infra/terraform/     AWS infra for services/api
docs/decisions/      ADRs
```

## Quickstart

```bash
# Backend
cp services/api/.env.example services/api/.env
cd services/api/src && pipenv install && pipenv run pytest -v

# Mobile
cd apps/mobile && npm install
```

# Ledger

A private household expense tracker for two people sharing one pooled
ledger. [`CLAUDE.md`](CLAUDE.md) is the living reference for this repo —
architecture, operating conventions (Jira, deployment, testing), and
project status — for anyone (human or agent) working here. (The original
`plan.md`/`DESIGN_BRIEF.md` planning docs have been removed now that the
project is fully built; see `CLAUDE.md`'s "Project status" section for a
summary of what they used to cover and where the build ended up diverging.)

## Status

All original phases (0-7) are built and **deployed live**:
https://w7ychchtd1.execute-api.ap-south-1.amazonaws.com (Lambda
`ledger-api` + HTTP API Gateway, `ap-south-1`, backed by a real MongoDB
Atlas cluster — note the API's routes are unprefixed at the root, not under
`/api`). Substantial post-MVP work has also landed: a dedicated loans
domain, a layered/explainable SMS parser, layered wallet/category SMS
prefill with a learning loop, a household-scoped merchant-alias/picker
layer, mobile FCM integration, and several UI/bugfix passes. See
`CLAUDE.md`'s "Project status" section for the full picture and known gaps.

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

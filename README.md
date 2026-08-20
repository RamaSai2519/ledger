# Ledger

A private household expense tracker for two people sharing one pooled
ledger. See [`DESIGN_BRIEF.md`](DESIGN_BRIEF.md) for the product/visual
brief and [`plan.md`](plan.md) for the full
backend + mobile architecture and phased roadmap. [`CLAUDE.md`](CLAUDE.md)
has operating conventions (Jira, deployment, testing) for anyone (human or
agent) working in this repo.

## Status

All phases (0-7) from `plan.md` §15 are built and **deployed live**:
https://w7ychchtd1.execute-api.ap-south-1.amazonaws.com (Lambda
`ledger-api` + HTTP API Gateway, `ap-south-1`, backed by a real MongoDB
Atlas cluster — note the API's routes are unprefixed at the root, not
under `/api` as `plan.md` §11 describes). Substantial post-MVP work has
also landed: a dedicated loans domain, a layered/explainable SMS parser,
layered wallet/category SMS prefill with a learning loop, mobile FCM
integration, and several UI/bugfix passes. See `CLAUDE.md`'s "Project
status" section for the full picture, known gaps, and where the plan
document has drifted from what's actually built.

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

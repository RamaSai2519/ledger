# ADR 0002: Flask + Flask-RESTful for the API

**Status:** Accepted

## Context

`plan.md` §3 specifies Python/Flask for the backend, deployed
as a zip Lambda. This mirrors the `models/<endpoint>/{main,validate,compute}.py`
+ `shared/{db,configs,uniservices}` structure already proven in
`~/Projects/journeymen`'s `services/api`, which keeps request validation,
business logic, and the Mongo access layer in separate, independently
testable files per endpoint.

## Decision

Flask + Flask-RESTful, one `models/<endpoint>/` package per action
(`main.py` orchestrates validate → compute, `validate.py` does plain input
validation, `compute.py` is the only place that touches Mongo), Resource
classes in `services/resources.py` wiring HTTP methods to `models.*.main.process`.

## Consequences

- Every endpoint's three concerns stay separately testable.
- A required dataclass field missing from a POST body raises a `TypeError`
  at `Input(**request_json)` construction time; `shared/after_request.py`
  registers a global `TypeError` handler that turns this into a clean 400
  instead of an unhandled 500 — `Input` fields stay plain required fields
  (they document the real contract) rather than being weakened to `Optional`.

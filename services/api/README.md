# services/api

Flask + Flask-RESTful backend, Python 3.13, zip-deployed Lambda, deployed
via Terraform + GitHub Actions. See
[`docs/decisions/0002-flask-rest-api.md`](../../docs/decisions/0002-flask-rest-api.md)
and [`docs/decisions/0003-terraform-github-actions-zip-lambda.md`](../../docs/decisions/0003-terraform-github-actions-zip-lambda.md).

**Status:** Phase 1 (Auth & Household) implemented and tested locally
(mongomock-backed pytest suite, 26/26 passing). Not yet deployed — see
`infra/terraform/README.md`'s bootstrap section for what's needed first.

## Layout

```
scripts/
  build_lambda_zip.sh    Builds the deployment zip — pip installs Pipfile's
                          [packages] as manylinux2014_x86_64 wheels, bundles
                          index.py/shared//services//models/
src/
  index.py                Flask app entry, Lambda handler(event, context) via aws-wsgi
  Pipfile                 dependency source of truth — installed by build_lambda_zip.sh
  conftest.py              pytest fixtures: mongomock-backed client, no external services needed
  shared/
    configs.py             ENV-switched CONFIG, all values from os.environ
    db.py                  get_x_collection() functions, lazy singleton Mongo client
    constants.py            default categories, invite code alphabet/length
    output.py                Output/success/failure helpers + exception types
    after_request.py         registers exception -> HTTP response error handlers
    auth_utils.py            password hashing, invite code generation, login lockout logic
  models/<endpoint>/
    main.py                 validate -> compute -> Output
    validate.py               plain input validation
    compute.py                the actual Mongo read/write
  services/
    resources.py              Flask-RESTful Resource classes
    controller.py              registers routes on the Api
  tests/
    test_<resource>.py         one file per endpoint
```

## Endpoints (Phase 1)

| Route | Methods | Auth | What |
|---|---|---|---|
| `/actions/health` | GET | none | liveness check |
| `/auth/signup` | POST | none | `mobile_number, password, name` |
| `/auth/login` | POST | none | `mobile_number, password` → tokens; locks out after 5 failed attempts for 15 min |
| `/auth/refresh` | POST | refresh token | → new access token |
| `/auth/logout` | POST | refresh token | revokes the refresh token (blocklist by `jti`) |
| `/auth/household/create` | POST | access token | `name` → creates household, seeds default categories |
| `/auth/household/join` | POST | access token | `invite_code` → joins an existing household (max 2 members) |
| `/auth/household/invite-code` | GET | access token | fetch the caller's household's invite code |
| `/auth/pin` | POST | access token | `pin` (4-6 digits) → sets local-app-lock PIN hash |

## Local development

```bash
cp services/api/.env.example services/api/.env   # fill in MONGO_URI at minimum
cd services/api/src
pipenv install
pipenv run python index.py   # boots on :8080
```

The app boots and every route registers even with `MONGO_URI` unset —
`/actions/health` works with nothing configured; Mongo-touching routes need
a real connection string.

## Testing

```bash
cd services/api/src
pipenv run pytest -v
```

`conftest.py` swaps `pymongo.MongoClient` for `mongomock`'s in-memory
equivalent — no real Mongo needed. Every endpoint's success path,
validation-failure path, and referential-integrity/security checks are
covered (duplicate signup, invalid invite code, full household, login
lockout, logout token revocation, missing-field 400s).

## Deployment

See `infra/terraform/README.md` for the one-time AWS bootstrap. Once that's
done, `.github/workflows/deploy-api.yml` builds the zip and applies
Terraform on every push to `main` touching this directory.

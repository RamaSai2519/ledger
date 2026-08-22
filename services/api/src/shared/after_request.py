import logging

from flask import Flask, request

from shared.output import AuthError, ConflictError, NotFoundError, ValidationError, failure

logger = logging.getLogger(__name__)


def _log_rejection(status: int, e: Exception) -> None:
    # 4xx rejections previously left zero trace in CloudWatch beyond the
    # generic Lambda REPORT line — a client-side failure (e.g. a background
    # SMS-ingest worker silently dropping a rejected request) was
    # undiagnosable from the backend side. Logged as a warning, not an
    # exception, since 4xx here is an expected/handled outcome, not a bug.
    logger.warning("%s %s -> %s: %s", request.method, request.path, status, e)


def register_error_handlers(app: Flask) -> None:
    # A POST handler builds its Input dataclass via Input(**request_json) — a
    # missing required field raises a plain TypeError before validate.py ever
    # runs. Caught centrally so that turns into a clean 400 instead of an
    # unhandled 500, without weakening Input fields to Optional.
    @app.errorhandler(TypeError)
    def handle_missing_field_error(e: TypeError):
        _log_rejection(400, e)
        return failure(f"missing_or_invalid_field: {e}", 400)

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        _log_rejection(400, e)
        return failure(str(e), 400)

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(e: NotFoundError):
        _log_rejection(404, e)
        return failure(str(e), 404)

    @app.errorhandler(ConflictError)
    def handle_conflict_error(e: ConflictError):
        _log_rejection(409, e)
        return failure(str(e), 409)

    @app.errorhandler(AuthError)
    def handle_auth_error(e: AuthError):
        _log_rejection(401, e)
        return failure(str(e), 401)

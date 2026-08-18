from flask import Flask

from shared.output import AuthError, ConflictError, NotFoundError, ValidationError, failure


def register_error_handlers(app: Flask) -> None:
    # A POST handler builds its Input dataclass via Input(**request_json) — a
    # missing required field raises a plain TypeError before validate.py ever
    # runs. Caught centrally so that turns into a clean 400 instead of an
    # unhandled 500, without weakening Input fields to Optional.
    @app.errorhandler(TypeError)
    def handle_missing_field_error(e: TypeError):
        return failure(f"missing_or_invalid_field: {e}", 400)

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        return failure(str(e), 400)

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(e: NotFoundError):
        return failure(str(e), 404)

    @app.errorhandler(ConflictError)
    def handle_conflict_error(e: ConflictError):
        return failure(str(e), 409)

    @app.errorhandler(AuthError)
    def handle_auth_error(e: AuthError):
        return failure(str(e), 401)

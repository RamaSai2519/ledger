"""Firebase Cloud Messaging push wiring (plan.md §3, LED-5).

No real Firebase project exists yet — FIREBASE_CREDENTIALS_JSON (see
shared/configs.py) is empty until the user completes that one-time console
setup, the same way MONGO_URI/JWT_SECRET_KEY started as placeholders before
their infra existed. `send_push` degrades gracefully when it's unset: it
logs a warning and no-ops rather than raising, so the rest of the
notification pipeline (in-app `notifications` collection writes) keeps
working standalone in dev/tests and until Firebase is configured.

Lazily initialized (not at import time) so importing this module never
requires credentials or network access — important for tests and for
Lambda cold starts when push isn't actually needed on a given invocation.
"""
import json
import logging

from shared.configs import CONFIG

logger = logging.getLogger(__name__)

_app = None
_init_attempted = False


def _get_app():
    global _app, _init_attempted
    if _init_attempted:
        return _app
    _init_attempted = True

    creds_json = CONFIG.get("firebase_credentials_json") or ""
    if not creds_json.strip():
        logger.warning("FIREBASE_CREDENTIALS_JSON not set; FCM push is a no-op")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(json.loads(creds_json))
        _app = firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("failed to initialize Firebase Admin SDK; FCM push is a no-op")
        _app = None
    return _app


def send_push(tokens: list[str], title: str, body: str, data: dict | None = None, data_only: bool = False) -> int:
    """Sends a push notification to each of `tokens`. Returns the number of
    tokens the send was attempted against (0 if FCM isn't configured, or
    `tokens` is empty). Never raises — a push failure must not break the
    surrounding job/endpoint, since the in-app `notifications` doc is the
    source of truth and push is best-effort delivery on top of it.

    `data_only=True` (LED-21) omits the `notification` payload entirely, so
    Android never auto-displays a default system notification — the client
    is trusted to build its own (via notifee) from `data` alone. Requires
    high delivery priority, since a data-only message is otherwise not
    guaranteed prompt delivery while the app is backgrounded/killed."""
    tokens = [t for t in (tokens or []) if t]
    if not tokens:
        return 0

    app = _get_app()
    if app is None:
        return 0

    try:
        from firebase_admin import messaging

        message = messaging.MulticastMessage(
            notification=None if data_only else messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            tokens=tokens,
            android=messaging.AndroidConfig(priority="high") if data_only else None,
        )
        messaging.send_each_for_multicast(message, app=app)
        return len(tokens)
    except Exception:
        logger.exception("FCM send failed")
        return 0

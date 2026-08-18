from datetime import datetime, timezone

import awsgi
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_restful import Api

from shared.after_request import register_error_handlers
from shared.configs import CONFIG
from shared.db import get_revoked_tokens_collection
from services.controller import register_routes

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = CONFIG["jwt_secret_key"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = CONFIG["access_token_minutes"] * 60
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = CONFIG["refresh_token_days"] * 24 * 60 * 60

jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def _check_if_token_revoked(jwt_header, jwt_payload) -> bool:
    revoked = get_revoked_tokens_collection().find_one({"jti": jwt_payload["jti"]})
    return revoked is not None


register_error_handlers(app)

api = Api(app)
register_routes(api)


def handler(event, context):
    return awsgi.response(app, event, context)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=CONFIG["debug"])

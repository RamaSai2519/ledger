from flask_jwt_extended import create_access_token

from shared.output import success


def process(user_id: str):
    return success({"access_token": create_access_token(identity=user_id)})

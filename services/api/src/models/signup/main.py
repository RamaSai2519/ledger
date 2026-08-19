
from flask_jwt_extended import create_access_token, create_refresh_token

from models.signup import compute, validate
from shared.interfaces import SignupInput as Input
from shared.output import success


def process(inp: Input):
    validate.validate(inp)
    user = compute.create_user(inp)
    user_id = str(user["_id"])
    return success(
        {
            "user_id": user_id,
            "name": user["name"],
            "access_token": create_access_token(identity=user_id),
            "refresh_token": create_refresh_token(identity=user_id),
        }
    )

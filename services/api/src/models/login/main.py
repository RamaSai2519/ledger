from dataclasses import dataclass

from flask_jwt_extended import create_access_token, create_refresh_token

from models.login import compute, validate
from shared.output import success


@dataclass
class Input:
    mobile_number: str
    password: str


def process(request_json: dict):
    inp = Input(**request_json)
    validate.validate(inp)
    user = compute.authenticate(inp)
    user_id = str(user["_id"])
    return success(
        {
            "user_id": user_id,
            "name": user["name"],
            "household_id": str(user["household_id"]) if user.get("household_id") else None,
            "access_token": create_access_token(identity=user_id),
            "refresh_token": create_refresh_token(identity=user_id),
        }
    )

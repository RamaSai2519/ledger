
from flask_jwt_extended import create_access_token

from shared.interfaces import RefreshInput as Input
from shared.output import success


def process(inp: Input):
    return success({"access_token": create_access_token(identity=inp.user_id)})

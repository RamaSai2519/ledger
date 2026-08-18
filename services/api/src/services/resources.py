from datetime import datetime, timezone

from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from flask_restful import Resource

from models.household_create import main as household_create
from models.household_invite_code import main as household_invite_code
from models.household_join import main as household_join
from models.login import main as login
from models.logout import main as logout
from models.pin_set import main as pin_set
from models.refresh import main as refresh
from models.signup import main as signup


class Health(Resource):
    def get(self):
        return {"status": "SUCCESS", "data": {"status": "ok"}, "error": None}, 200


class Signup(Resource):
    def post(self):
        return signup.process(request.get_json(force=True) or {})


class Login(Resource):
    def post(self):
        return login.process(request.get_json(force=True) or {})


class Refresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        return refresh.process(get_jwt_identity())


class Logout(Resource):
    @jwt_required(refresh=True)
    def post(self):
        claims = get_jwt()
        expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        return logout.process(claims["jti"], expires_at)


class HouseholdCreate(Resource):
    @jwt_required()
    def post(self):
        return household_create.process(request.get_json(force=True) or {}, get_jwt_identity())


class HouseholdJoin(Resource):
    @jwt_required()
    def post(self):
        return household_join.process(request.get_json(force=True) or {}, get_jwt_identity())


class HouseholdInviteCode(Resource):
    @jwt_required()
    def get(self):
        return household_invite_code.process(get_jwt_identity())


class PinSet(Resource):
    @jwt_required()
    def post(self):
        return pin_set.process(request.get_json(force=True) or {}, get_jwt_identity())

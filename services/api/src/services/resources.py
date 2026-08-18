from datetime import datetime, timezone

from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from flask_restful import Resource

from models.category_create import main as category_create
from models.category_delete import main as category_delete
from models.category_list import main as category_list
from models.category_update import main as category_update
from models.household_create import main as household_create
from models.household_invite_code import main as household_invite_code
from models.household_join import main as household_join
from models.login import main as login
from models.logout import main as logout
from models.pin_set import main as pin_set
from models.refresh import main as refresh
from models.signup import main as signup
from models.transaction_create import main as transaction_create
from models.transaction_delete import main as transaction_delete
from models.transaction_get import main as transaction_get
from models.transaction_list import main as transaction_list
from models.transaction_transfer import main as transaction_transfer
from models.transaction_update import main as transaction_update
from models.wallet_balance_history import main as wallet_balance_history
from models.wallet_create import main as wallet_create
from models.wallet_delete import main as wallet_delete
from models.wallet_get import main as wallet_get
from models.wallet_list import main as wallet_list
from models.wallet_reconcile import main as wallet_reconcile
from models.wallet_update import main as wallet_update


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


class Wallets(Resource):
    @jwt_required()
    def get(self):
        return wallet_list.process(get_jwt_identity(), request.args.to_dict())

    @jwt_required()
    def post(self):
        return wallet_create.process(request.get_json(force=True) or {}, get_jwt_identity())


class WalletDetail(Resource):
    @jwt_required()
    def get(self, wallet_id):
        return wallet_get.process(wallet_id, get_jwt_identity())

    @jwt_required()
    def patch(self, wallet_id):
        return wallet_update.process(wallet_id, request.get_json(force=True) or {}, get_jwt_identity())

    @jwt_required()
    def delete(self, wallet_id):
        return wallet_delete.process(wallet_id, get_jwt_identity())


class WalletReconcile(Resource):
    @jwt_required()
    def post(self, wallet_id):
        return wallet_reconcile.process(wallet_id, request.get_json(force=True) or {}, get_jwt_identity())


class WalletBalanceHistory(Resource):
    @jwt_required()
    def get(self, wallet_id):
        return wallet_balance_history.process(wallet_id, get_jwt_identity(), request.args.to_dict())


class Categories(Resource):
    @jwt_required()
    def get(self):
        return category_list.process(get_jwt_identity(), request.args.to_dict())

    @jwt_required()
    def post(self):
        return category_create.process(request.get_json(force=True) or {}, get_jwt_identity())


class CategoryDetail(Resource):
    @jwt_required()
    def patch(self, category_id):
        return category_update.process(category_id, request.get_json(force=True) or {}, get_jwt_identity())

    @jwt_required()
    def delete(self, category_id):
        return category_delete.process(category_id, get_jwt_identity())


class Transactions(Resource):
    @jwt_required()
    def get(self):
        return transaction_list.process(get_jwt_identity(), request.args.to_dict())

    @jwt_required()
    def post(self):
        return transaction_create.process(request.get_json(force=True) or {}, get_jwt_identity())


class TransactionDetail(Resource):
    @jwt_required()
    def get(self, transaction_id):
        return transaction_get.process(transaction_id, get_jwt_identity())

    @jwt_required()
    def patch(self, transaction_id):
        return transaction_update.process(transaction_id, request.get_json(force=True) or {}, get_jwt_identity())

    @jwt_required()
    def delete(self, transaction_id):
        return transaction_delete.process(transaction_id, get_jwt_identity())


class TransactionTransfer(Resource):
    @jwt_required()
    def post(self):
        return transaction_transfer.process(request.get_json(force=True) or {}, get_jwt_identity())

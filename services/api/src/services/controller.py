from flask_restful import Api

from services.resources import (
    CategoryDetail,
    Categories,
    Health,
    HouseholdCreate,
    HouseholdInviteCode,
    HouseholdJoin,
    Login,
    Logout,
    PinSet,
    Refresh,
    Signup,
    TransactionDetail,
    Transactions,
    TransactionTransfer,
    WalletBalanceHistory,
    WalletDetail,
    WalletReconcile,
    Wallets,
)


def register_routes(api: Api) -> None:
    api.add_resource(Health, "/actions/health")
    api.add_resource(Signup, "/auth/signup")
    api.add_resource(Login, "/auth/login")
    api.add_resource(Refresh, "/auth/refresh")
    api.add_resource(Logout, "/auth/logout")
    api.add_resource(HouseholdCreate, "/auth/household/create")
    api.add_resource(HouseholdJoin, "/auth/household/join")
    api.add_resource(HouseholdInviteCode, "/auth/household/invite-code")
    api.add_resource(PinSet, "/auth/pin")

    api.add_resource(Wallets, "/wallets")
    api.add_resource(WalletDetail, "/wallets/<string:wallet_id>")
    api.add_resource(WalletReconcile, "/wallets/<string:wallet_id>/reconcile")
    api.add_resource(WalletBalanceHistory, "/wallets/<string:wallet_id>/balance-history")

    api.add_resource(Categories, "/categories")
    api.add_resource(CategoryDetail, "/categories/<string:category_id>")

    api.add_resource(Transactions, "/transactions")
    api.add_resource(TransactionTransfer, "/transactions/transfer")
    api.add_resource(TransactionDetail, "/transactions/<string:transaction_id>")

from flask_restful import Api

from services.resources import (
    Health,
    HouseholdCreate,
    HouseholdInviteCode,
    HouseholdJoin,
    Login,
    Logout,
    PinSet,
    Refresh,
    Signup,
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

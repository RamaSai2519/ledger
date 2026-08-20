from datetime import datetime, timezone

from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from flask_restful import Resource

from models.budget_create import main as budget_create
from models.budget_delete import main as budget_delete
from models.budget_list import main as budget_list
from models.budget_progress import main as budget_progress
from models.budget_update import main as budget_update
from models.category_create import main as category_create
from models.category_delete import main as category_delete
from models.category_list import main as category_list
from models.category_update import main as category_update
from models.fcm_token_register import main as fcm_token_register
from models.household_create import main as household_create
from models.household_invite_code import main as household_invite_code
from models.household_join import main as household_join
from models.insight_category_breakdown import main as insight_category_breakdown
from models.insight_income_vs_expense import main as insight_income_vs_expense
from models.insight_net_worth_history import main as insight_net_worth_history
from models.insight_trends import main as insight_trends
from models.loan_create import main as loan_create
from models.loan_delete import main as loan_delete
from models.loan_list import main as loan_list
from models.loan_update import main as loan_update
from models.login import main as login
from models.logout import main as logout
from models.notification_list import main as notification_list
from models.notification_read import main as notification_read
from models.pin_set import main as pin_set
from models.recurring_rule_create import main as recurring_rule_create
from models.recurring_rule_delete import main as recurring_rule_delete
from models.recurring_rule_list import main as recurring_rule_list
from models.recurring_rule_skip_next import main as recurring_rule_skip_next
from models.recurring_rule_update import main as recurring_rule_update
from models.refresh import main as refresh
from models.signup import main as signup
from models.sms_ingest import main as sms_ingest
from models.sms_parser_rules_create import main as sms_parser_rules_create
from models.sms_parser_rules_list import main as sms_parser_rules_list
from models.sms_suggestion_accept import main as sms_suggestion_accept
from models.sms_suggestion_dismiss import main as sms_suggestion_dismiss
from models.sms_suggestions_list import main as sms_suggestions_list
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
from shared.input import build_input
from shared.output import success


def _body() -> dict:
    return request.get_json(silent=True) or {}


class Health(Resource):
    def get(self):
        return success({"status": "ok"})


class Signup(Resource):
    def post(self):
        return signup.process(build_input(signup.Input, _body()))


class Login(Resource):
    def post(self):
        return login.process(build_input(login.Input, _body()))


class Refresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        return refresh.process(refresh.Input(user_id=get_jwt_identity()))


class Logout(Resource):
    @jwt_required(refresh=True)
    def post(self):
        claims = get_jwt()
        expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        return logout.process(logout.Input(jti=claims["jti"], expires_at=expires_at))


class HouseholdCreate(Resource):
    @jwt_required()
    def post(self):
        return household_create.process(build_input(household_create.Input, _body(), user_id=get_jwt_identity()))


class HouseholdJoin(Resource):
    @jwt_required()
    def post(self):
        return household_join.process(build_input(household_join.Input, _body(), user_id=get_jwt_identity()))


class HouseholdInviteCode(Resource):
    @jwt_required()
    def get(self):
        return household_invite_code.process(household_invite_code.Input(user_id=get_jwt_identity()))


class PinSet(Resource):
    @jwt_required()
    def post(self):
        return pin_set.process(build_input(pin_set.Input, _body(), user_id=get_jwt_identity()))


class Wallets(Resource):
    @jwt_required()
    def get(self):
        return wallet_list.process(build_input(wallet_list.Input, request.args.to_dict(), user_id=get_jwt_identity()))

    @jwt_required()
    def post(self):
        return wallet_create.process(build_input(wallet_create.Input, _body(), user_id=get_jwt_identity()))


class WalletDetail(Resource):
    @jwt_required()
    def get(self, wallet_id):
        return wallet_get.process(wallet_get.Input(wallet_id=wallet_id, user_id=get_jwt_identity()))

    @jwt_required()
    def patch(self, wallet_id):
        return wallet_update.process(wallet_update.Input(body=_body(), wallet_id=wallet_id, user_id=get_jwt_identity()))

    @jwt_required()
    def delete(self, wallet_id):
        return wallet_delete.process(wallet_delete.Input(wallet_id=wallet_id, user_id=get_jwt_identity()))


class WalletReconcile(Resource):
    @jwt_required()
    def post(self, wallet_id):
        return wallet_reconcile.process(
            build_input(wallet_reconcile.Input, _body(), wallet_id=wallet_id, user_id=get_jwt_identity())
        )


class WalletBalanceHistory(Resource):
    @jwt_required()
    def get(self, wallet_id):
        return wallet_balance_history.process(
            build_input(
                wallet_balance_history.Input,
                request.args.to_dict(),
                aliases={"from_": "from"},
                wallet_id=wallet_id,
                user_id=get_jwt_identity(),
            )
        )


class Categories(Resource):
    @jwt_required()
    def get(self):
        return category_list.process(build_input(category_list.Input, request.args.to_dict(), user_id=get_jwt_identity()))

    @jwt_required()
    def post(self):
        return category_create.process(build_input(category_create.Input, _body(), user_id=get_jwt_identity()))


class CategoryDetail(Resource):
    @jwt_required()
    def patch(self, category_id):
        return category_update.process(
            category_update.Input(body=_body(), category_id=category_id, user_id=get_jwt_identity())
        )

    @jwt_required()
    def delete(self, category_id):
        return category_delete.process(category_delete.Input(category_id=category_id, user_id=get_jwt_identity()))


class Transactions(Resource):
    @jwt_required()
    def get(self):
        return transaction_list.process(
            build_input(
                transaction_list.Input,
                request.args.to_dict(),
                aliases={"from_": "from"},
                requesting_user_id=get_jwt_identity(),
            )
        )

    @jwt_required()
    def post(self):
        return transaction_create.process(build_input(transaction_create.Input, _body(), user_id=get_jwt_identity()))


class TransactionDetail(Resource):
    @jwt_required()
    def get(self, transaction_id):
        return transaction_get.process(transaction_get.Input(transaction_id=transaction_id, user_id=get_jwt_identity()))

    @jwt_required()
    def patch(self, transaction_id):
        return transaction_update.process(
            transaction_update.Input(body=_body(), transaction_id=transaction_id, user_id=get_jwt_identity())
        )

    @jwt_required()
    def delete(self, transaction_id):
        return transaction_delete.process(
            transaction_delete.Input(transaction_id=transaction_id, user_id=get_jwt_identity())
        )


class TransactionTransfer(Resource):
    @jwt_required()
    def post(self):
        return transaction_transfer.process(
            build_input(transaction_transfer.Input, _body(), user_id=get_jwt_identity())
        )


class FcmTokenRegister(Resource):
    @jwt_required()
    def post(self):
        return fcm_token_register.process(build_input(fcm_token_register.Input, _body(), user_id=get_jwt_identity()))


class Budgets(Resource):
    @jwt_required()
    def get(self):
        return budget_list.process(build_input(budget_list.Input, request.args.to_dict(), user_id=get_jwt_identity()))

    @jwt_required()
    def post(self):
        return budget_create.process(build_input(budget_create.Input, _body(), user_id=get_jwt_identity()))


class BudgetDetail(Resource):
    @jwt_required()
    def patch(self, budget_id):
        return budget_update.process(budget_update.Input(body=_body(), budget_id=budget_id, user_id=get_jwt_identity()))

    @jwt_required()
    def delete(self, budget_id):
        return budget_delete.process(budget_delete.Input(budget_id=budget_id, user_id=get_jwt_identity()))


class BudgetProgress(Resource):
    @jwt_required()
    def get(self, budget_id):
        return budget_progress.process(budget_progress.Input(budget_id=budget_id, user_id=get_jwt_identity()))


class RecurringRules(Resource):
    @jwt_required()
    def get(self):
        return recurring_rule_list.process(
            build_input(recurring_rule_list.Input, request.args.to_dict(), user_id=get_jwt_identity())
        )

    @jwt_required()
    def post(self):
        return recurring_rule_create.process(
            build_input(recurring_rule_create.Input, _body(), user_id=get_jwt_identity())
        )


class RecurringRuleDetail(Resource):
    @jwt_required()
    def patch(self, rule_id):
        return recurring_rule_update.process(
            recurring_rule_update.Input(body=_body(), rule_id=rule_id, user_id=get_jwt_identity())
        )

    @jwt_required()
    def delete(self, rule_id):
        return recurring_rule_delete.process(recurring_rule_delete.Input(rule_id=rule_id, user_id=get_jwt_identity()))


class RecurringRuleSkipNext(Resource):
    @jwt_required()
    def post(self, rule_id):
        return recurring_rule_skip_next.process(
            recurring_rule_skip_next.Input(rule_id=rule_id, user_id=get_jwt_identity())
        )


class Loans(Resource):
    @jwt_required()
    def get(self):
        return loan_list.process(build_input(loan_list.Input, request.args.to_dict(), user_id=get_jwt_identity()))

    @jwt_required()
    def post(self):
        return loan_create.process(build_input(loan_create.Input, _body(), user_id=get_jwt_identity()))


class LoanDetail(Resource):
    @jwt_required()
    def patch(self, loan_id):
        return loan_update.process(loan_update.Input(body=_body(), loan_id=loan_id, user_id=get_jwt_identity()))

    @jwt_required()
    def delete(self, loan_id):
        return loan_delete.process(loan_delete.Input(loan_id=loan_id, user_id=get_jwt_identity()))


class InsightTrends(Resource):
    @jwt_required()
    def get(self):
        return insight_trends.process(
            build_input(insight_trends.Input, request.args.to_dict(), aliases={"from_": "from"}, user_id=get_jwt_identity())
        )


class InsightIncomeVsExpense(Resource):
    @jwt_required()
    def get(self):
        return insight_income_vs_expense.process(
            build_input(
                insight_income_vs_expense.Input,
                request.args.to_dict(),
                aliases={"from_": "from"},
                user_id=get_jwt_identity(),
            )
        )


class InsightCategoryBreakdown(Resource):
    @jwt_required()
    def get(self):
        return insight_category_breakdown.process(
            build_input(
                insight_category_breakdown.Input,
                request.args.to_dict(),
                aliases={"from_": "from"},
                user_id=get_jwt_identity(),
            )
        )


class InsightNetWorthHistory(Resource):
    @jwt_required()
    def get(self):
        return insight_net_worth_history.process(
            build_input(
                insight_net_worth_history.Input,
                request.args.to_dict(),
                aliases={"from_": "from"},
                user_id=get_jwt_identity(),
            )
        )


class Notifications(Resource):
    @jwt_required()
    def get(self):
        return notification_list.process(
            build_input(notification_list.Input, request.args.to_dict(), requesting_user_id=get_jwt_identity())
        )


class NotificationRead(Resource):
    @jwt_required()
    def post(self, notification_id):
        return notification_read.process(
            notification_read.Input(notification_id=notification_id, user_id=get_jwt_identity())
        )


class SmsIngest(Resource):
    @jwt_required()
    def post(self):
        return sms_ingest.process(build_input(sms_ingest.Input, _body(), user_id=get_jwt_identity()))


class SmsSuggestions(Resource):
    @jwt_required()
    def get(self):
        return sms_suggestions_list.process(sms_suggestions_list.Input(user_id=get_jwt_identity()))


class SmsSuggestionAccept(Resource):
    @jwt_required()
    def post(self, sms_id):
        return sms_suggestion_accept.process(
            build_input(sms_suggestion_accept.Input, _body(), sms_id=sms_id, user_id=get_jwt_identity())
        )


class SmsSuggestionDismiss(Resource):
    @jwt_required()
    def post(self, sms_id):
        return sms_suggestion_dismiss.process(sms_suggestion_dismiss.Input(sms_id=sms_id, user_id=get_jwt_identity()))


class SmsParserRules(Resource):
    @jwt_required()
    def get(self):
        return sms_parser_rules_list.process(sms_parser_rules_list.Input(user_id=get_jwt_identity()))

    @jwt_required()
    def post(self):
        return sms_parser_rules_create.process(
            build_input(sms_parser_rules_create.Input, _body(), user_id=get_jwt_identity())
        )

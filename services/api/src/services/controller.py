from flask_restful import Api

from services.resources import (
    BudgetDetail,
    BudgetProgress,
    Budgets,
    CategoryDetail,
    CategoryReorder,
    Categories,
    FcmTokenRegister,
    Health,
    HouseholdCreate,
    HouseholdInviteCode,
    HouseholdJoin,
    HouseholdPreview,
    InsightCategoryBreakdown,
    InsightIncomeVsExpense,
    InsightNetWorthHistory,
    InsightTrends,
    LoanDetail,
    Loans,
    Login,
    Logout,
    Merchants,
    NotificationRead,
    Notifications,
    PinSet,
    RecurringRuleDetail,
    RecurringRuleSkipNext,
    RecurringRules,
    Refresh,
    Signup,
    SmsIngest,
    SmsParserRules,
    SmsSuggestionAccept,
    SmsSuggestionDismiss,
    SmsSuggestions,
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
    api.add_resource(HouseholdPreview, "/auth/household/preview")
    api.add_resource(PinSet, "/auth/pin")

    api.add_resource(Wallets, "/wallets")
    api.add_resource(WalletDetail, "/wallets/<string:wallet_id>")
    api.add_resource(WalletReconcile, "/wallets/<string:wallet_id>/reconcile")
    api.add_resource(WalletBalanceHistory, "/wallets/<string:wallet_id>/balance-history")

    api.add_resource(Categories, "/categories")
    api.add_resource(CategoryReorder, "/categories/reorder")
    api.add_resource(CategoryDetail, "/categories/<string:category_id>")

    api.add_resource(Transactions, "/transactions")
    api.add_resource(TransactionTransfer, "/transactions/transfer")
    api.add_resource(TransactionDetail, "/transactions/<string:transaction_id>")

    api.add_resource(FcmTokenRegister, "/users/fcm-token")

    api.add_resource(RecurringRules, "/recurring")
    api.add_resource(RecurringRuleDetail, "/recurring/<string:rule_id>")
    api.add_resource(RecurringRuleSkipNext, "/recurring/<string:rule_id>/skip-next")

    api.add_resource(Loans, "/loans")
    api.add_resource(LoanDetail, "/loans/<string:loan_id>")

    api.add_resource(Budgets, "/budgets")
    api.add_resource(BudgetDetail, "/budgets/<string:budget_id>")
    api.add_resource(BudgetProgress, "/budgets/<string:budget_id>/progress")

    api.add_resource(InsightTrends, "/insights/trends")
    api.add_resource(InsightIncomeVsExpense, "/insights/income-vs-expense")
    api.add_resource(InsightCategoryBreakdown, "/insights/category-breakdown")
    api.add_resource(InsightNetWorthHistory, "/insights/net-worth-history")

    api.add_resource(Notifications, "/notifications")
    api.add_resource(NotificationRead, "/notifications/<string:notification_id>/read")

    api.add_resource(Merchants, "/merchants")

    api.add_resource(SmsIngest, "/sms/ingest")
    api.add_resource(SmsSuggestions, "/sms/suggestions")
    api.add_resource(SmsSuggestionAccept, "/sms/suggestions/<string:sms_id>/accept")
    api.add_resource(SmsSuggestionDismiss, "/sms/suggestions/<string:sms_id>/dismiss")
    api.add_resource(SmsParserRules, "/sms/parser-rules")

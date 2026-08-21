"""Every route's `Input` dataclass, in one place — the single definition of
what each route accepts, whether the client-supplied part comes from a JSON
body or query-string args. Each model's main.py imports its own class from
here (as `Input`) rather than declaring one inline, so the full input
surface of the API is visible from one file instead of scattered across
~50 model directories.

Fields populated by the resource layer (JWT identity, URL path params, JWT
claims) are documented per-field below — see shared/input.py's build_input,
which always overrides any client-supplied value for those fields.

PATCH endpoints take a raw `body: dict` field instead of individually typed
fields: a partial update must distinguish "field omitted" from "field
explicitly set to null/false", which a dataclass with Optional defaults
can't express. Each such model's own validate.py allowlists/typechecks
`body` field-by-field (PATCHABLE_FIELDS/IMMUTABLE_FIELDS).
"""
from dataclasses import dataclass, field
from datetime import datetime


# ── auth / household ─────────────────────────────────────────────────────


@dataclass
class SignupInput:
    mobile_number: str
    password: str
    name: str


@dataclass
class LoginInput:
    mobile_number: str
    password: str


@dataclass
class RefreshInput:
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class LogoutInput:
    jti: str | None = None  # populated by the resource from the JWT claims
    expires_at: datetime | None = None  # populated by the resource from the JWT claims


@dataclass
class HouseholdCreateInput:
    name: str = "My Household"
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class HouseholdJoinInput:
    invite_code: str = ""
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class HouseholdInviteCodeInput:
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class HouseholdPreviewInput:
    invite_code: str = ""
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class PinSetInput:
    pin: str = ""
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── wallets ───────────────────────────────────────────────────────────────


@dataclass
class WalletCreateInput:
    name: str = ""
    type: str = ""
    provider: str | None = None
    account_last4: str | None = None
    opening_balance: float = 0
    currency: str = "INR"
    icon: str | None = None
    color: str | None = None
    credit_card_details: dict | None = None
    pay_later_details: dict | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class WalletListInput:
    include_archived: str | None = None
    type: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class WalletGetInput:
    wallet_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class WalletUpdateInput:
    body: dict = field(default_factory=dict)
    wallet_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class WalletDeleteInput:
    wallet_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class WalletReconcileInput:
    actual_balance: float = 0
    wallet_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class WalletBalanceHistoryInput:
    from_: str | None = None  # wire name "from" — see shared/input.py's aliases param
    to: str | None = None
    wallet_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── categories ────────────────────────────────────────────────────────────


@dataclass
class CategoryCreateInput:
    name: str = ""
    type: str = ""
    icon: str | None = None
    color: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class CategoryListInput:
    include_archived: str | None = None
    type: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class CategoryUpdateInput:
    body: dict = field(default_factory=dict)
    category_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class CategoryDeleteInput:
    category_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class CategoryReorderInput:
    order: list = field(default_factory=list)
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── transactions ──────────────────────────────────────────────────────────


@dataclass
class TransactionCreateInput:
    wallet_id: str = ""
    category_id: str = ""
    type: str = ""
    amount: float = 0
    merchant_name: str | None = None
    note: str | None = None
    date: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class TransactionListInput:
    wallet_id: str | None = None
    category_id: str | None = None
    loan_id: str | None = None
    user_id: str | None = None  # a filter value here — the client MAY set this
    type: str | None = None
    from_: str | None = None  # wire name "from"
    to: str | None = None
    page: str | None = None
    page_size: str | None = None
    requesting_user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class TransactionGetInput:
    transaction_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class TransactionUpdateInput:
    body: dict = field(default_factory=dict)
    transaction_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class TransactionDeleteInput:
    transaction_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class TransactionTransferInput:
    wallet_id: str = ""
    transfer_to_wallet_id: str = ""
    amount: float = 0
    note: str | None = None
    date: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── budgets ───────────────────────────────────────────────────────────────


@dataclass
class BudgetCreateInput:
    scope: str = ""
    amount: float = 0
    scope_ref_id: str | None = None
    period: str = "monthly"
    threshold_percents: list | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class BudgetListInput:
    scope: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class BudgetUpdateInput:
    body: dict = field(default_factory=dict)
    budget_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class BudgetDeleteInput:
    budget_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class BudgetProgressInput:
    budget_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── recurring rules ───────────────────────────────────────────────────────


@dataclass
class RecurringRuleCreateInput:
    wallet_id: str = ""
    category_id: str = ""
    type: str = ""
    merchant_name: str = ""
    frequency: str = ""
    next_due_date: str = ""
    amount: float | None = None
    auto_create: bool = False
    is_active: bool = True
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class RecurringRuleListInput:
    is_active: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class RecurringRuleUpdateInput:
    body: dict = field(default_factory=dict)
    rule_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class RecurringRuleDeleteInput:
    rule_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class RecurringRuleSkipNextInput:
    rule_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── loans ─────────────────────────────────────────────────────────────────


@dataclass
class LoanCreateInput:
    name: str = ""
    wallet_id: str = ""
    category_id: str = ""
    principal: float = 0
    annual_interest_rate: float = 0
    tenure_months: int = 0
    emi_amount: float = 0
    start_date: str = ""
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class LoanListInput:
    is_active: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class LoanUpdateInput:
    body: dict = field(default_factory=dict)
    loan_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class LoanDeleteInput:
    loan_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── insights ──────────────────────────────────────────────────────────────


@dataclass
class InsightTrendsInput:
    period: str | None = None
    from_: str | None = None  # wire name "from"
    to: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class InsightIncomeVsExpenseInput:
    period: str | None = None
    from_: str | None = None  # wire name "from"
    to: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class InsightCategoryBreakdownInput:
    period: str | None = None
    from_: str | None = None  # wire name "from"
    to: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class InsightNetWorthHistoryInput:
    from_: str | None = None  # wire name "from"
    to: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── notifications ─────────────────────────────────────────────────────────


@dataclass
class NotificationListInput:
    user_id: str | None = None  # a filter value here ("me") — the client MAY set this
    is_read: str | None = None
    page: str | None = None
    page_size: str | None = None
    requesting_user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class NotificationReadInput:
    notification_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── fcm ───────────────────────────────────────────────────────────────────


@dataclass
class FcmTokenRegisterInput:
    token: str = ""
    user_id: str | None = None  # populated by the resource from the JWT identity


# ── sms ───────────────────────────────────────────────────────────────────


@dataclass
class SmsIngestInput:
    raw_text: str = ""
    sender_id: str = ""
    received_at: str | None = None
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class SmsSuggestionsListInput:
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class SmsSuggestionAcceptInput:
    wallet_id: str | None = None
    category_id: str | None = None
    amount: float | None = None
    type: str | None = None
    date: str | None = None
    # LED-28: a picked-existing or freshly-typed canonical merchant name -
    # when set, becomes the transaction's merchant_name (instead of the raw
    # parsed text) and writes a household merchant_aliases entry + keys the
    # learned category/wallet maps off it, so future SMS for this merchant
    # (even a differently bank-truncated raw variant) resolve consistently.
    merchant_name: str | None = None
    sms_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class MerchantListInput:
    q: str | None = None  # optional case-insensitive substring filter
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class SmsSuggestionDismissInput:
    sms_id: str | None = None  # populated by the resource from the URL
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class SmsParserRulesCreateInput:
    bank_code: str = ""
    sender_ids: list = field(default_factory=list)
    patterns: list = field(default_factory=list)
    is_active: bool = True
    user_id: str | None = None  # populated by the resource from the JWT identity


@dataclass
class SmsParserRulesListInput:
    user_id: str | None = None  # populated by the resource from the JWT identity

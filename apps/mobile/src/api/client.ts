import {useAuthStore} from '@/state/authStore';

// `terraform output api_url` in infra/terraform — update if the stack is
// ever torn down and recreated (API Gateway assigns a new id).
const API_BASE_URL = 'https://w7ychchtd1.execute-api.ap-south-1.amazonaws.com';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: {method?: string; body?: unknown; auth?: 'access' | 'refresh' | 'none'} = {},
): Promise<T> {
  const {method = 'GET', body, auth = 'access'} = options;
  const headers: Record<string, string> = {'Content-Type': 'application/json'};

  if (auth !== 'none') {
    const token =
      auth === 'refresh' ? useAuthStore.getState().refreshToken : useAuthStore.getState().accessToken;
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const json = await response.json();
  if (json.status !== 'SUCCESS') {
    throw new ApiError(json.error ?? 'unknown_error', response.status);
  }
  return json.data as T;
}

export type SignupInput = {mobile_number: string; password: string; name: string};
export type LoginInput = {mobile_number: string; password: string};
export type AuthTokens = {
  user_id: string;
  name: string;
  access_token: string;
  refresh_token: string;
  household_id?: string | null;
};

export const authApi = {
  signup: (input: SignupInput) => request<AuthTokens>('/auth/signup', {method: 'POST', body: input, auth: 'none'}),
  login: (input: LoginInput) => request<AuthTokens>('/auth/login', {method: 'POST', body: input, auth: 'none'}),
  logout: () => request<{logged_out: boolean}>('/auth/logout', {method: 'POST', auth: 'refresh'}),
  refresh: () => request<{access_token: string}>('/auth/refresh', {method: 'POST', auth: 'refresh'}),
};

export const householdApi = {
  create: (name: string) =>
    request<{household_id: string; name: string; invite_code: string}>('/auth/household/create', {
      method: 'POST',
      body: {name},
    }),
  join: (invite_code: string) =>
    request<{household_id: string; name: string; member_count: number}>('/auth/household/join', {
      method: 'POST',
      body: {invite_code},
    }),
  inviteCode: () =>
    request<{invite_code: string; household_id: string}>('/auth/household/invite-code'),
  preview: (invite_code: string) =>
    request<{name: string; member_count: number; created_at: string}>(
      withQuery('/auth/household/preview', {invite_code}),
    ),
};

function withQuery(path: string, params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return path;
  const pairs: string[] = [];
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  });
  return pairs.length ? `${path}?${pairs.join('&')}` : path;
}

// ---- Core Ledger (LED-4): wallets, categories, transactions ----

// "loan" was removed as a wallet type (LED-14) — loans now live in their
// own dedicated collection/domain, see LoanApi below.
export type WalletType = 'bank_account' | 'credit_card' | 'pay_later' | 'cash';

export type CreditCardDetails = {
  credit_limit?: number;
  statement_day?: number;
  due_day?: number;
  min_due_percent?: number;
};
export type PayLaterDetails = {credit_limit?: number; billing_cycle_day?: number; due_day?: number};

export type Wallet = {
  id: string;
  household_id: string;
  name: string;
  type: WalletType;
  provider: string | null;
  account_last4: string | null;
  opening_balance: number;
  current_balance: number;
  currency: string;
  icon: string | null;
  color: string | null;
  is_archived: boolean;
  is_default: boolean;
  credit_card_details: CreditCardDetails | null;
  pay_later_details: PayLaterDetails | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type WalletCreateInput = {
  name: string;
  type: WalletType;
  provider?: string;
  account_last4?: string;
  opening_balance?: number;
  currency?: string;
  icon?: string;
  color?: string;
  credit_card_details?: CreditCardDetails;
  pay_later_details?: PayLaterDetails;
};

export type WalletUpdateInput = Partial<
  Pick<
    Wallet,
    | 'name'
    | 'provider'
    | 'account_last4'
    | 'icon'
    | 'color'
    | 'is_archived'
    | 'is_default'
    | 'credit_card_details'
    | 'pay_later_details'
  >
>;

export type BalanceHistoryPoint = {
  date: string | null;
  balance: number;
  transaction_id?: string;
  label: string;
};

export const walletsApi = {
  list: (params?: {include_archived?: boolean; type?: WalletType}) =>
    request<{wallets: Wallet[]}>(withQuery('/wallets', params as Record<string, string>)),
  get: (id: string) => request<Wallet>(`/wallets/${id}`),
  create: (input: WalletCreateInput) => request<Wallet>('/wallets', {method: 'POST', body: input}),
  update: (id: string, input: WalletUpdateInput) =>
    request<Wallet>(`/wallets/${id}`, {method: 'PATCH', body: input}),
  archive: (id: string) => request<{id: string; is_archived: boolean}>(`/wallets/${id}`, {method: 'DELETE'}),
  reconcile: (id: string, actual_balance: number) =>
    request<{wallet: Wallet; adjustment_transaction: Transaction; delta: number}>(`/wallets/${id}/reconcile`, {
      method: 'POST',
      body: {actual_balance},
    }),
  balanceHistory: (id: string, params?: {from?: string; to?: string}) =>
    request<{wallet_id: string; points: BalanceHistoryPoint[]}>(
      withQuery(`/wallets/${id}/balance-history`, params),
    ),
};

export type CategoryType = 'expense' | 'income';

export type Category = {
  id: string;
  household_id: string;
  name: string;
  type: CategoryType;
  icon: string | null;
  color: string | null;
  is_default: boolean;
  is_archived: boolean;
  sort_order: number;
};

export type CategoryCreateInput = {name: string; type: CategoryType; icon?: string; color?: string};
export type CategoryUpdateInput = Partial<Pick<Category, 'name' | 'icon' | 'color' | 'is_archived'>>;

export const categoriesApi = {
  list: (params?: {include_archived?: boolean; type?: CategoryType}) =>
    request<{categories: Category[]}>(withQuery('/categories', params as Record<string, string>)),
  create: (input: CategoryCreateInput) => request<Category>('/categories', {method: 'POST', body: input}),
  update: (id: string, input: CategoryUpdateInput) =>
    request<Category>(`/categories/${id}`, {method: 'PATCH', body: input}),
  remove: (id: string) =>
    request<{id: string; hard_deleted?: boolean; is_archived?: boolean}>(`/categories/${id}`, {method: 'DELETE'}),
  reorder: (order: string[]) =>
    request<{categories: Category[]}>('/categories/reorder', {method: 'PATCH', body: {order}}),
};

export type TransactionType = 'expense' | 'income' | 'transfer' | 'adjustment';

export type Transaction = {
  id: string;
  household_id: string;
  wallet_id: string;
  category_id: string | null;
  user_id: string;
  type: TransactionType;
  amount: number;
  transfer_to_wallet_id: string | null;
  merchant_name: string | null;
  note: string | null;
  date: string;
  source: string;
  sms_id: string | null;
  recurring_rule_id: string | null;
  loan_id: string | null;
  created_at: string;
  updated_at: string;
};

export type TransactionCreateInput = {
  wallet_id: string;
  category_id: string;
  type: 'expense' | 'income';
  amount: number;
  merchant_name?: string;
  note?: string;
  date?: string;
};

export type TransactionUpdateInput = Partial<{
  wallet_id: string;
  category_id: string;
  amount: number;
  merchant_name: string;
  note: string;
  date: string;
}>;

export type TransactionListParams = {
  wallet_id?: string;
  category_id?: string;
  loan_id?: string;
  user_id?: string;
  type?: TransactionType;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
};

export type TransactionListResult = {
  transactions: Transaction[];
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
};

export const transactionsApi = {
  list: (params?: TransactionListParams) =>
    request<TransactionListResult>(withQuery('/transactions', params as Record<string, string>)),
  get: (id: string) => request<Transaction>(`/transactions/${id}`),
  create: (input: TransactionCreateInput) => request<Transaction>('/transactions', {method: 'POST', body: input}),
  update: (id: string, input: TransactionUpdateInput) =>
    request<Transaction>(`/transactions/${id}`, {method: 'PATCH', body: input}),
  remove: (id: string) => request<{id: string; deleted: boolean}>(`/transactions/${id}`, {method: 'DELETE'}),
  transfer: (input: {wallet_id: string; transfer_to_wallet_id: string; amount: number; note?: string; date?: string}) =>
    request<Transaction>('/transactions/transfer', {method: 'POST', body: input}),
};

// ---- Budgets & Notifications (LED-5) ----

export type BudgetScope = 'category' | 'wallet' | 'overall';

export type Budget = {
  id: string;
  household_id: string;
  scope: BudgetScope;
  scope_ref_id: string | null;
  amount: number;
  period: 'monthly';
  threshold_percents: number[];
  created_at: string;
  updated_at: string;
};

export type BudgetCreateInput = {
  scope: BudgetScope;
  amount: number;
  scope_ref_id?: string;
  threshold_percents?: number[];
};

export type BudgetUpdateInput = Partial<{amount: number; threshold_percents: number[]}>;

export type BudgetProgress = {
  budget_id: string;
  spent: number;
  amount: number;
  percent: number;
  period_start: string;
  period_end: string;
  thresholds: number[];
  crossed_thresholds: number[];
};

export const budgetsApi = {
  list: (params?: {scope?: BudgetScope}) =>
    request<{budgets: Budget[]}>(withQuery('/budgets', params as Record<string, string>)),
  create: (input: BudgetCreateInput) => request<Budget>('/budgets', {method: 'POST', body: input}),
  update: (id: string, input: BudgetUpdateInput) => request<Budget>(`/budgets/${id}`, {method: 'PATCH', body: input}),
  remove: (id: string) => request<{id: string; deleted: boolean}>(`/budgets/${id}`, {method: 'DELETE'}),
  progress: (id: string) => request<BudgetProgress>(`/budgets/${id}/progress`),
};

export type NotificationType = 'budget_threshold' | 'budget_exceeded' | 'sms_suggestion' | 'digest' | 'bill_due' | 'recurring_reminder';

export type Notification = {
  id: string;
  household_id: string;
  user_id: string;
  type: NotificationType;
  payload: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
};

export type NotificationListResult = {
  notifications: Notification[];
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
};

export const notificationsApi = {
  list: (params?: {page?: number; page_size?: number; user_id?: 'me'; is_read?: 'true' | 'false'}) =>
    request<NotificationListResult>(withQuery('/notifications', params as Record<string, string>)),
  markRead: (id: string) => request<Notification>(`/notifications/${id}/read`, {method: 'POST'}),
};

// ---- Insights (LED-6) ----

export type InsightPeriod = 'daily' | 'monthly' | 'yearly';

export type TrendPoint = {bucket: string; expense: number; income: number};
export type TrendsResult = {period: InsightPeriod; from: string; to: string; points: TrendPoint[]};

export type IncomeVsExpensePoint = {bucket: string; income: number; expense: number; net: number};
export type IncomeVsExpenseResult = {
  period: InsightPeriod;
  from: string;
  to: string;
  points: IncomeVsExpensePoint[];
};

export type CategoryBreakdownItem = {
  category_id: string;
  category_name: string;
  category_color: string | null;
  category_icon: string | null;
  amount: number;
};
export type CategoryBreakdownResult = {
  period: InsightPeriod;
  from: string;
  to: string;
  items: CategoryBreakdownItem[];
};

export type NetWorthSnapshot = {
  date: string | null;
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
  per_wallet_breakdown: Record<string, number>;
};
export type NetWorthHistoryResult = {from: string; to: string; snapshots: NetWorthSnapshot[]};

export type InsightRangeParams = {period?: InsightPeriod; from?: string; to?: string};

export const insightsApi = {
  trends: (params?: InsightRangeParams) =>
    request<TrendsResult>(withQuery('/insights/trends', params as Record<string, string>)),
  incomeVsExpense: (params?: InsightRangeParams) =>
    request<IncomeVsExpenseResult>(withQuery('/insights/income-vs-expense', params as Record<string, string>)),
  categoryBreakdown: (params?: InsightRangeParams) =>
    request<CategoryBreakdownResult>(withQuery('/insights/category-breakdown', params as Record<string, string>)),
  netWorthHistory: (params?: {from?: string; to?: string}) =>
    request<NetWorthHistoryResult>(withQuery('/insights/net-worth-history', params)),
};

export const fcmApi = {
  registerToken: (token: string) => request<{registered: boolean}>('/users/fcm-token', {method: 'POST', body: {token}}),
};

// ---- SMS Pipeline (LED-7) ----
// raw_text is deliberately never returned by the backend serializer (data
// minimization, plan.md §2.3) — screens only ever see the already-extracted
// structured fields below, never the original message text.

export type SmsInboxSuggestion = {
  id: string;
  household_id: string;
  user_id: string;
  sender_id: string;
  received_at: string;
  parse_status: 'pending' | 'parsed' | 'ignored' | 'failed';
  parsed_amount: number | null;
  parsed_direction: 'debit' | 'credit' | null;
  parsed_last4: string | null;
  parsed_merchant: string | null;
  parsed_ref: string | null;
  suggested_wallet_id: string | null;
  suggested_category_id: string | null;
  wallet_confidence: number;
  category_confidence: number;
  confidence_score: number;
  status: 'suggested' | 'accepted' | 'dismissed';
  resolved_transaction_id: string | null;
  created_at: string;
  updated_at: string;
};

export type SmsSuggestionAcceptInput = Partial<{
  wallet_id: string;
  category_id: string;
  amount: number;
  type: 'expense' | 'income';
  date: string;
}>;

// ---- Recurring Transactions (LED-8) ----

export type RecurringFrequency = 'weekly' | 'monthly' | 'yearly';

export type RecurringRule = {
  id: string;
  household_id: string;
  wallet_id: string;
  category_id: string;
  type: 'expense' | 'income';
  merchant_name: string;
  amount: number | null;
  frequency: RecurringFrequency;
  next_due_date: string;
  auto_detected: boolean;
  auto_create: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type RecurringRuleCreateInput = {
  wallet_id: string;
  category_id: string;
  type: 'expense' | 'income';
  merchant_name: string;
  frequency: RecurringFrequency;
  next_due_date: string;
  amount?: number;
  auto_create?: boolean;
  is_active?: boolean;
};

export type RecurringRuleUpdateInput = Partial<
  Omit<RecurringRuleCreateInput, 'wallet_id' | 'category_id'> & {wallet_id: string; category_id: string}
>;

export const recurringApi = {
  list: (params?: {is_active?: boolean}) =>
    request<{recurring_rules: RecurringRule[]}>(withQuery('/recurring', params as Record<string, string>)),
  create: (input: RecurringRuleCreateInput) => request<RecurringRule>('/recurring', {method: 'POST', body: input}),
  update: (id: string, input: RecurringRuleUpdateInput) => request<RecurringRule>(`/recurring/${id}`, {method: 'PATCH', body: input}),
  remove: (id: string) => request<{id: string; deleted: boolean}>(`/recurring/${id}`, {method: 'DELETE'}),
  skipNext: (id: string) => request<RecurringRule>(`/recurring/${id}/skip-next`, {method: 'POST'}),
};

// ---- Loans (LED-14) ----

export type Loan = {
  id: string;
  household_id: string;
  name: string;
  wallet_id: string;
  category_id: string;
  principal: number;
  annual_interest_rate: number;
  tenure_months: number;
  emi_amount: number;
  outstanding_balance: number;
  start_date: string;
  next_due_date: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LoanCreateInput = {
  name: string;
  wallet_id: string;
  category_id: string;
  principal: number;
  annual_interest_rate: number;
  tenure_months: number;
  emi_amount: number;
  start_date: string;
};

export type LoanUpdateInput = Partial<
  Pick<Loan, 'name' | 'emi_amount' | 'is_active' | 'wallet_id' | 'category_id'>
>;

export const loansApi = {
  // No GET /loans/<id> on the backend (mirrors recurring_rules, which also
  // has no single-resource GET) — LoanDetailScreen fetches via list() and
  // finds the loan by id.
  list: (params?: {is_active?: boolean}) =>
    request<{loans: Loan[]}>(withQuery('/loans', params as Record<string, string>)),
  create: (input: LoanCreateInput) => request<Loan>('/loans', {method: 'POST', body: input}),
  update: (id: string, input: LoanUpdateInput) => request<Loan>(`/loans/${id}`, {method: 'PATCH', body: input}),
  remove: (id: string) => request<{id: string; deleted: boolean}>(`/loans/${id}`, {method: 'DELETE'}),
};

export const smsApi = {
  suggestions: () => request<{suggestions: SmsInboxSuggestion[]}>('/sms/suggestions'),
  accept: (id: string, input?: SmsSuggestionAcceptInput) =>
    request<Transaction>(`/sms/suggestions/${id}/accept`, {method: 'POST', body: input ?? {}}),
  dismiss: (id: string) => request<SmsInboxSuggestion>(`/sms/suggestions/${id}/dismiss`, {method: 'POST'}),
};

export {ApiError};

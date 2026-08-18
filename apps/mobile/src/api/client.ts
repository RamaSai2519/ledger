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
};

function withQuery(path: string, params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return path;
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') usp.set(key, String(value));
  });
  const qs = usp.toString();
  return qs ? `${path}?${qs}` : path;
}

// ---- Core Ledger (LED-4): wallets, categories, transactions ----

export type WalletType = 'bank_account' | 'credit_card' | 'pay_later' | 'cash' | 'loan';

export type CreditCardDetails = {
  credit_limit?: number;
  statement_day?: number;
  due_day?: number;
  min_due_percent?: number;
};
export type PayLaterDetails = {credit_limit?: number; billing_cycle_day?: number; due_day?: number};
export type LoanDetails = {
  principal?: number;
  interest_rate?: number;
  tenure_months?: number;
  emi_amount?: number;
  start_date?: string;
};

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
  credit_card_details: CreditCardDetails | null;
  pay_later_details: PayLaterDetails | null;
  loan_details: LoanDetails | null;
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
  loan_details?: LoanDetails;
};

export type WalletUpdateInput = Partial<
  Pick<
    Wallet,
    'name' | 'provider' | 'account_last4' | 'icon' | 'color' | 'is_archived' | 'credit_card_details' | 'pay_later_details' | 'loan_details'
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

export type NotificationType = 'budget_threshold' | 'budget_exceeded' | 'sms_suggestion' | 'digest' | 'bill_due';

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
  list: (params?: {page?: number; page_size?: number}) =>
    request<NotificationListResult>(withQuery('/notifications', params as Record<string, string>)),
  markRead: (id: string) => request<Notification>(`/notifications/${id}/read`, {method: 'POST'}),
};

export const fcmApi = {
  registerToken: (token: string) => request<{registered: boolean}>('/users/fcm-token', {method: 'POST', body: {token}}),
};

export {ApiError};

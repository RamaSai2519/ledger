export type RootStackParamList = {
  Splash: undefined;
  Onboarding: undefined;
  SignUp: undefined;
  Login: undefined;
  HouseholdCreate: undefined;
  HouseholdJoin: undefined;
  SmsPermissionRationale: undefined;
  PinSetup: undefined;
  AppLock: undefined;
  Home: undefined;
  WalletsList: undefined;
  WalletDetail: {walletId: string};
  WalletForm: {walletId?: string} | undefined;
  WalletReconcile: {walletId: string};
  TransactionForm:
    | {transactionId?: string; walletId?: string; mode?: 'expense' | 'income' | 'transfer'; toWalletId?: string}
    | undefined;
  Categories: undefined;
  BudgetsList: undefined;
  BudgetForm: {budgetId?: string} | undefined;
  Insights: undefined;
  Notifications: undefined;
  SmsSuggestionEdit: {suggestion: import('@/api/client').SmsInboxSuggestion};
  Settings: undefined;
  TransactionsList: undefined;
  RecurringRulesList: undefined;
  RecurringRuleForm: {ruleId?: string} | undefined;
};

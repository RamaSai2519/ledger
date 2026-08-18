export type RootStackParamList = {
  Splash: undefined;
  SignUp: undefined;
  Login: undefined;
  HouseholdChoice: undefined;
  HouseholdCreate: undefined;
  HouseholdJoin: undefined;
  Home: undefined;
  WalletsList: undefined;
  WalletDetail: {walletId: string};
  WalletForm: {walletId?: string} | undefined;
  WalletReconcile: {walletId: string};
  TransactionForm: {transactionId?: string; walletId?: string} | undefined;
  Categories: undefined;
  BudgetsList: undefined;
  BudgetForm: {budgetId?: string} | undefined;
  Insights: undefined;
  Notifications: undefined;
};

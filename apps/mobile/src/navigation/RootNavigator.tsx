import React, {useEffect, useRef} from 'react';
import {AppState} from 'react-native';
import {NavigationContainer, DarkTheme, createNavigationContainerRef} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {SplashScreen} from '@/screens/SplashScreen';
import {OnboardingScreen} from '@/screens/OnboardingScreen';
import {SignUpScreen} from '@/screens/SignUpScreen';
import {LoginScreen} from '@/screens/LoginScreen';
import {HouseholdCreateScreen} from '@/screens/HouseholdCreateScreen';
import {HouseholdJoinScreen} from '@/screens/HouseholdJoinScreen';
import {PinSetupScreen} from '@/screens/PinSetupScreen';
import {AppLockScreen} from '@/screens/AppLockScreen';
import {HomeScreen} from '@/screens/HomeScreen';
import {WalletsListScreen} from '@/screens/WalletsListScreen';
import {WalletDetailScreen} from '@/screens/WalletDetailScreen';
import {WalletFormScreen} from '@/screens/WalletFormScreen';
import {WalletReconcileScreen} from '@/screens/WalletReconcileScreen';
import {TransactionFormScreen} from '@/screens/TransactionFormScreen';
import {TransactionsListScreen} from '@/screens/TransactionsListScreen';
import {CategoriesScreen} from '@/screens/CategoriesScreen';
import {BudgetsListScreen} from '@/screens/BudgetsListScreen';
import {BudgetFormScreen} from '@/screens/BudgetFormScreen';
import {InsightsScreen} from '@/screens/InsightsScreen';
import {NotificationsScreen} from '@/screens/NotificationsScreen';
import {SmsPermissionRationaleScreen} from '@/screens/SmsPermissionRationaleScreen';
import {SmsSuggestionEditScreen} from '@/screens/SmsSuggestionEditScreen';
import {SettingsScreen} from '@/screens/SettingsScreen';
import {RecurringRulesListScreen} from '@/screens/RecurringRulesListScreen';
import {RecurringRuleFormScreen} from '@/screens/RecurringRuleFormScreen';
import {useAuthStore} from '@/state/authStore';
import {colors} from '@/theme/tokens';

const Stack = createNativeStackNavigator<RootStackParamList>();

const theme = {
  ...DarkTheme,
  colors: {...DarkTheme.colors, background: colors.background, card: colors.surface, primary: colors.accent, border: colors.border},
};

const navigationRef = createNavigationContainerRef<RootStackParamList>();

// Screens where landing on AppLock would interrupt something already in
// progress (auth/onboarding chain, or AppLock itself) — the foreground
// listener below skips re-locking while any of these is the active route.
const LOCK_EXEMPT_ROUTES = new Set<keyof RootStackParamList>([
  'Splash',
  'Onboarding',
  'SignUp',
  'Login',
  'HouseholdCreate',
  'HouseholdJoin',
  'SmsPermissionRationale',
  'PinSetup',
  'AppLock',
]);

// plan.md §5.5: "App lock ... on app foreground/launch, require PIN ...
// before rendering any data." There's no native secure-storage/lifecycle
// module here, so this uses AppState (core React Native, no extra
// dependency) — on every background→active transition, if a PIN has been
// set for this session, push AppLock over whatever screen was showing.
function useAppLockGate() {
  const appState = useRef(AppState.currentState);

  useEffect(() => {
    const sub = AppState.addEventListener('change', (nextState) => {
      const wasBackground = appState.current.match(/inactive|background/);
      appState.current = nextState;
      if (!wasBackground || nextState !== 'active') return;

      const {pinHash, accessToken} = useAuthStore.getState();
      if (!pinHash || !accessToken || !navigationRef.isReady()) return;

      const currentRoute = navigationRef.getCurrentRoute()?.name as keyof RootStackParamList | undefined;
      if (currentRoute && LOCK_EXEMPT_ROUTES.has(currentRoute)) return;

      navigationRef.navigate('AppLock');
    });
    return () => sub.remove();
  }, []);
}

export function RootNavigator() {
  useAppLockGate();

  return (
    <NavigationContainer ref={navigationRef} theme={theme}>
      <Stack.Navigator
        screenOptions={{
          headerShown: false,
          headerStyle: {backgroundColor: colors.background},
          headerTintColor: colors.textPrimary,
          headerShadowVisible: false,
        }}>
        <Stack.Screen name="Splash" component={SplashScreen} />
        <Stack.Screen name="Onboarding" component={OnboardingScreen} />
        <Stack.Screen name="SignUp" component={SignUpScreen} options={{headerShown: true, title: ''}} />
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="HouseholdCreate" component={HouseholdCreateScreen} options={{headerShown: true, title: ''}} />
        <Stack.Screen name="HouseholdJoin" component={HouseholdJoinScreen} options={{headerShown: true, title: ''}} />
        <Stack.Screen name="PinSetup" component={PinSetupScreen} options={{headerShown: true, title: ''}} />
        <Stack.Screen name="AppLock" component={AppLockScreen} />
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="WalletsList" component={WalletsListScreen} />
        <Stack.Screen name="WalletDetail" component={WalletDetailScreen} options={{headerShown: true, title: 'Wallet'}} />
        <Stack.Screen name="WalletForm" component={WalletFormScreen} options={{headerShown: true, title: 'Wallet'}} />
        <Stack.Screen
          name="WalletReconcile"
          component={WalletReconcileScreen}
          options={{headerShown: true, title: 'Reconcile'}}
        />
        <Stack.Screen
          name="TransactionForm"
          component={TransactionFormScreen}
          options={{headerShown: true, title: 'Transaction'}}
        />
        <Stack.Screen
          name="TransactionsList"
          component={TransactionsListScreen}
          options={{headerShown: true, title: 'Transactions'}}
        />
        <Stack.Screen name="Categories" component={CategoriesScreen} options={{headerShown: true, title: 'Categories'}} />
        <Stack.Screen name="BudgetsList" component={BudgetsListScreen} options={{headerShown: true, title: 'Budgets'}} />
        <Stack.Screen name="BudgetForm" component={BudgetFormScreen} options={{headerShown: true, title: 'Budget'}} />
        <Stack.Screen name="Insights" component={InsightsScreen} />
        <Stack.Screen
          name="Notifications"
          component={NotificationsScreen}
          options={{headerShown: true, title: 'Notifications'}}
        />
        <Stack.Screen
          name="SmsPermissionRationale"
          component={SmsPermissionRationaleScreen}
          options={{headerShown: true, title: ''}}
        />
        <Stack.Screen
          name="SmsSuggestionEdit"
          component={SmsSuggestionEditScreen}
          options={{headerShown: true, title: 'Edit suggestion'}}
        />
        <Stack.Screen name="Settings" component={SettingsScreen} />
        <Stack.Screen
          name="RecurringRulesList"
          component={RecurringRulesListScreen}
          options={{headerShown: true, title: 'Recurring'}}
        />
        <Stack.Screen
          name="RecurringRuleForm"
          component={RecurringRuleFormScreen}
          options={{headerShown: true, title: 'Recurring rule'}}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

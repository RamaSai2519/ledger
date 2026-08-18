import React from 'react';
import {NavigationContainer, DarkTheme} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {SplashScreen} from '@/screens/SplashScreen';
import {SignUpScreen} from '@/screens/SignUpScreen';
import {LoginScreen} from '@/screens/LoginScreen';
import {HouseholdChoiceScreen} from '@/screens/HouseholdChoiceScreen';
import {HouseholdCreateScreen} from '@/screens/HouseholdCreateScreen';
import {HouseholdJoinScreen} from '@/screens/HouseholdJoinScreen';
import {HomeScreen} from '@/screens/HomeScreen';
import {WalletsListScreen} from '@/screens/WalletsListScreen';
import {WalletDetailScreen} from '@/screens/WalletDetailScreen';
import {WalletFormScreen} from '@/screens/WalletFormScreen';
import {WalletReconcileScreen} from '@/screens/WalletReconcileScreen';
import {TransactionFormScreen} from '@/screens/TransactionFormScreen';
import {CategoriesScreen} from '@/screens/CategoriesScreen';
import {BudgetsListScreen} from '@/screens/BudgetsListScreen';
import {BudgetFormScreen} from '@/screens/BudgetFormScreen';
import {InsightsScreen} from '@/screens/InsightsScreen';
import {NotificationsScreen} from '@/screens/NotificationsScreen';
import {colors} from '@/theme/tokens';

const Stack = createNativeStackNavigator<RootStackParamList>();

const theme = {
  ...DarkTheme,
  colors: {...DarkTheme.colors, background: colors.background, card: colors.surface, primary: colors.accent},
};

export function RootNavigator() {
  return (
    <NavigationContainer theme={theme}>
      <Stack.Navigator screenOptions={{headerShown: false}}>
        <Stack.Screen name="Splash" component={SplashScreen} />
        <Stack.Screen name="SignUp" component={SignUpScreen} />
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="HouseholdChoice" component={HouseholdChoiceScreen} />
        <Stack.Screen name="HouseholdCreate" component={HouseholdCreateScreen} />
        <Stack.Screen name="HouseholdJoin" component={HouseholdJoinScreen} />
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="WalletsList" component={WalletsListScreen} options={{headerShown: true, title: 'Wallets'}} />
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
        <Stack.Screen name="Categories" component={CategoriesScreen} options={{headerShown: true, title: 'Categories'}} />
        <Stack.Screen name="BudgetsList" component={BudgetsListScreen} options={{headerShown: true, title: 'Budgets'}} />
        <Stack.Screen name="BudgetForm" component={BudgetFormScreen} options={{headerShown: true, title: 'Budget'}} />
        <Stack.Screen name="Insights" component={InsightsScreen} options={{headerShown: true, title: 'Insights'}} />
        <Stack.Screen
          name="Notifications"
          component={NotificationsScreen}
          options={{headerShown: true, title: 'Notifications'}}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

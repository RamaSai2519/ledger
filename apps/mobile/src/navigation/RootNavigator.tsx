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
      </Stack.Navigator>
    </NavigationContainer>
  );
}

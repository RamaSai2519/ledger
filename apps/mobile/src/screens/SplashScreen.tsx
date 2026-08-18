import React, {useEffect} from 'react';
import {ActivityIndicator, StyleSheet, Text, View} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {colors, spacing} from '@/theme/tokens';
import {useAuthStore} from '@/state/authStore';

type Props = NativeStackScreenProps<RootStackParamList, 'Splash'>;

export function SplashScreen({navigation}: Props) {
  const {accessToken, householdId} = useAuthStore();

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!accessToken) {
        navigation.replace('Login');
      } else if (!householdId) {
        navigation.replace('HouseholdChoice');
      } else {
        navigation.replace('Home');
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [accessToken, householdId, navigation]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Ledger</Text>
      <ActivityIndicator color={colors.accent} style={{marginTop: spacing.lg}} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    color: colors.textPrimary,
    fontSize: 32,
    fontWeight: '600',
  },
});

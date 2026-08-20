import React, {useEffect} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {colors, fontFamilies, radius} from '@/theme/tokens';
import {LogoMark} from '@/components/LogoMark';
import {useAuthStore} from '@/state/authStore';

type Props = NativeStackScreenProps<RootStackParamList, 'Splash'>;

// s01 in the design project: gradient app-mark tile, wordmark, tagline, and
// a bottom progress bar. Now uses the actual Ledger logo mark (design
// project "Logo design iteration", option 1a) instead of the placeholder
// "L" letter tile.
export function SplashScreen({navigation}: Props) {
  const {accessToken, householdId, pinHash, hydrated, hydrate} = useAuthStore();

  // LED-9: accessToken only ever lived in memory, so before the Keychain-backed
  // rehydrate below existed, every cold start looked logged-out even for a
  // returning user with a valid refresh token. hydrate() silently attempts
  // /auth/refresh from the persisted session before this screen routes.
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!hydrated) return;
    const timer = setTimeout(() => {
      if (!accessToken) {
        navigation.replace('Onboarding');
      } else if (!householdId) {
        navigation.replace('HouseholdCreate');
      } else if (pinHash) {
        navigation.replace('AppLock');
      } else {
        navigation.replace('Home');
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [accessToken, householdId, pinHash, hydrated, navigation]);

  return (
    <View style={styles.container}>
      <View style={styles.mark}>
        <LogoMark size={44} />
      </View>
      <Text style={styles.title}>Ledger</Text>
      <Text style={styles.tagline}>One book, two people</Text>
      <View style={styles.progressTrack}>
        <View style={styles.progressFill} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, alignItems: 'center', justifyContent: 'center', gap: 18},
  mark: {
    width: 76,
    height: 76,
    borderRadius: radius.card,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 26, letterSpacing: -0.4},
  tagline: {color: colors.textSecondary, fontSize: 12.5},
  progressTrack: {
    position: 'absolute',
    bottom: 34,
    width: 44,
    height: 3,
    borderRadius: 2,
    backgroundColor: colors.border,
    overflow: 'hidden',
  },
  progressFill: {width: '60%', height: '100%', backgroundColor: colors.accent},
});

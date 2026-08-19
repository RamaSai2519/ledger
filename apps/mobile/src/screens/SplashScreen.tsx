import React, {useEffect} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {colors, fontFamilies, radius} from '@/theme/tokens';
import {useAuthStore} from '@/state/authStore';

type Props = NativeStackScreenProps<RootStackParamList, 'Splash'>;

// s01 in the design project: gradient app-mark tile, wordmark, tagline, and
// a bottom progress bar. The mockup labels the tile "K" for the design
// project's working name ("Khaata") — CLAUDE.md is explicit that name never
// propagates into this repo, so it's "L" for Ledger here. No
// react-native-linear-gradient dependency exists yet (tokens.ts's
// heroGradient is unused pending that), so the tile falls back to the flat
// accent color rather than adding a new native dependency for one screen.
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
        <Text style={styles.markText}>L</Text>
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
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  markText: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 38, fontWeight: '600'},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 26, letterSpacing: -0.4, fontWeight: '600'},
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

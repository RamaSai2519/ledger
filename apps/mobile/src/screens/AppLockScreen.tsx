import React, {useEffect, useState} from 'react';
import {Pressable, StyleSheet, Text, View} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {PinKeypad} from '@/components/PinKeypad';
import {promptBiometricUnlock} from '@/native/biometrics';
import {useAuthStore} from '@/state/authStore';
import {colors, fontFamilies, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'AppLock'>;

const PIN_LENGTH = 4;

// s10 in the design project — shown on every app open/foreground when a PIN
// has been set (wired via the AppState listener in RootNavigator).
export function AppLockScreen({navigation}: Props) {
  const [digits, setDigits] = useState('');
  const [error, setError] = useState(false);
  const householdName = useAuthStore((s) => s.householdName);
  const verifyPin = useAuthStore((s) => s.verifyPin);
  const clearSession = useAuthStore((s) => s.clearSession);
  const biometricEnabled = useAuthStore((s) => s.biometricEnabled);

  const tryBiometricUnlock = async () => {
    if (!biometricEnabled) return;
    const success = await promptBiometricUnlock();
    if (success) navigation.replace('Home');
  };

  // Auto-prompt once on mount when the user has opted in from Settings —
  // still falls through to the PIN pad on cancel/failure/no-sensor.
  useEffect(() => {
    tryBiometricUnlock();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onDigit = (d: string) => {
    if (digits.length >= PIN_LENGTH) return;
    const next = digits + d;
    setError(false);
    if (next.length === PIN_LENGTH) {
      if (verifyPin(next)) {
        navigation.replace('Home');
      } else {
        setError(true);
        setDigits('');
      }
    } else {
      setDigits(next);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.mark}>
          <Text style={styles.markText}>L</Text>
        </View>
        <Text style={styles.title}>Enter your PIN</Text>
        {!!householdName && <Text style={styles.subtitle}>{householdName}</Text>}
      </View>

      <View style={styles.dots}>
        {Array.from({length: PIN_LENGTH}).map((_, i) => (
          <View key={i} style={[styles.dot, i < digits.length && styles.dotFilled, error && styles.dotError]} />
        ))}
      </View>

      <View style={{flex: 1}} />

      <View style={styles.keypadWrap}>
        <PinKeypad
          variant="circle"
          onDigit={onDigit}
          onBackspace={() => setDigits((d) => d.slice(0, -1))}
          rightSlot={
            biometricEnabled ? (
              <Pressable onPress={tryBiometricUnlock} hitSlop={12}>
                <Text style={styles.fingerprintGlyph}>⚷</Text>
              </Pressable>
            ) : undefined
          }
        />
      </View>
      <Pressable
        onPress={() => {
          clearSession();
          navigation.replace('Login');
        }}>
        <Text style={styles.forgot}>Forgot PIN? Log in again</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, paddingHorizontal: spacing.lg, paddingBottom: spacing.md},
  header: {alignItems: 'center', gap: spacing.xs, paddingTop: 40},
  mark: {width: 46, height: 46, borderRadius: 15, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  markText: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 23, fontWeight: '600'},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 19, fontWeight: '600'},
  subtitle: {color: colors.textSecondary, fontSize: 12.5},
  dots: {flexDirection: 'row', justifyContent: 'center', gap: 14, paddingTop: spacing.lg},
  dot: {width: 14, height: 14, borderRadius: 7, backgroundColor: colors.border},
  dotFilled: {backgroundColor: colors.accent},
  dotError: {backgroundColor: colors.negative},
  keypadWrap: {paddingHorizontal: 16, paddingBottom: spacing.sm},
  fingerprintGlyph: {fontSize: 26, color: colors.accentOnDark},
  forgot: {textAlign: 'center', fontSize: 12.5, color: colors.textSecondary, paddingBottom: spacing.md},
});

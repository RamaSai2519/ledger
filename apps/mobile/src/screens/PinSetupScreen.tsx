import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, View} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {PinKeypad} from '@/components/PinKeypad';
import {useAuthStore} from '@/state/authStore';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'PinSetup'>;

const PIN_LENGTH = 4;

// s09 in the design project. Two phases on the same layout — enter, then
// confirm by re-entering — since a single blind 4-digit entry risks a typo
// locking the household out with no PIN recovery beyond "log in again"
// (plan.md §5.5 explicitly skips server-side PIN recovery for MVP).
export function PinSetupScreen({navigation}: Props) {
  const [firstPin, setFirstPin] = useState<string | null>(null);
  const [digits, setDigits] = useState('');
  const [biometricEnabled, setBiometricEnabled] = useState(true);
  const [mismatch, setMismatch] = useState(false);
  const setPin = useAuthStore((s) => s.setPin);

  const onDigit = (d: string) => {
    if (digits.length >= PIN_LENGTH) return;
    const next = digits + d;
    setMismatch(false);
    if (next.length === PIN_LENGTH) {
      if (!firstPin) {
        setFirstPin(next);
        setDigits('');
      } else if (next === firstPin) {
        setPin(next);
        navigation.replace('Home');
      } else {
        setMismatch(true);
        setFirstPin(null);
        setDigits('');
      }
    } else {
      setDigits(next);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerBlock}>
        <Text style={styles.title}>{firstPin ? 'Confirm your PIN' : 'Set a 4-digit PIN'}</Text>
        <Text style={styles.subtitle}>
          {mismatch ? "Those didn't match — try again." : 'Ledger asks for it every time you open the app.'}
        </Text>
      </View>

      <View style={styles.dots}>
        {Array.from({length: PIN_LENGTH}).map((_, i) => (
          <View key={i} style={[styles.dot, i < digits.length && styles.dotFilled]} />
        ))}
      </View>

      {!firstPin && (
        <Pressable style={styles.biometricRow} onPress={() => setBiometricEnabled((v) => !v)}>
          <View style={styles.biometricLeft}>
            <Text style={styles.biometricGlyph}>⚷</Text>
            <View>
              <Text style={styles.biometricTitle}>Use fingerprint too</Text>
              <Text style={styles.biometricSubtitle}>Faster unlock, same PIN as backup.</Text>
            </View>
          </View>
          <View style={[styles.toggleTrack, biometricEnabled && styles.toggleTrackOn]}>
            <View style={[styles.toggleThumb, biometricEnabled && styles.toggleThumbOn]} />
          </View>
        </Pressable>
      )}

      <View style={{flex: 1}} />

      <View style={styles.keypadWrap}>
        <PinKeypad variant="square" onDigit={onDigit} onBackspace={() => setDigits((d) => d.slice(0, -1))} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, paddingHorizontal: spacing.lg, paddingBottom: spacing.xl},
  headerBlock: {paddingTop: spacing.sm, alignItems: 'center'},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 24, letterSpacing: -0.4, fontWeight: '600'},
  subtitle: {color: colors.textSecondary, fontSize: 13, marginTop: spacing.xs, textAlign: 'center'},
  dots: {flexDirection: 'row', justifyContent: 'center', gap: 14, paddingTop: spacing.xl},
  dot: {width: 14, height: 14, borderRadius: 7, backgroundColor: colors.border},
  dotFilled: {backgroundColor: colors.accent},
  biometricRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: spacing.lg,
    padding: 14,
    borderRadius: radius.row,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  biometricLeft: {flexDirection: 'row', alignItems: 'center', gap: spacing.sm, flex: 1},
  biometricGlyph: {fontSize: 20, color: colors.accentOnDark},
  biometricTitle: {fontSize: 13, fontWeight: '600', color: colors.textPrimary},
  biometricSubtitle: {fontSize: 11.5, color: colors.textSecondary, marginTop: 2},
  toggleTrack: {width: 44, height: 26, borderRadius: radius.pill, backgroundColor: colors.border, padding: 3, justifyContent: 'center'},
  toggleTrackOn: {backgroundColor: colors.accent, alignItems: 'flex-end'},
  toggleThumb: {width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff'},
  toggleThumbOn: {},
  keypadWrap: {paddingHorizontal: 16},
});

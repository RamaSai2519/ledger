import React from 'react';
import {Pressable, StyleSheet, Text, View} from 'react-native';
import {colors, fontFamilies} from '@/theme/tokens';

type Props = {
  variant: 'square' | 'circle';
  onDigit: (digit: string) => void;
  onBackspace: () => void;
  rightSlot?: React.ReactNode;
};

const DIGITS = ['1', '2', '3', '4', '5', '6', '7', '8', '9'];

// Shared numeric keypad for PinSetupScreen (s09, rounded-square keys) and
// AppLockScreen (s10, circular keys) — same 3x4 grid/backspace logic, only
// the key shape and the bottom-left slot (biometric icon on the lock
// screen, nothing on setup) differ.
export function PinKeypad({variant, onDigit, onBackspace, rightSlot}: Props) {
  const keyStyle = variant === 'square' ? styles.keySquare : styles.keyCircle;
  return (
    <View style={styles.grid}>
      {DIGITS.map((d) => (
        <Pressable key={d} style={keyStyle} onPress={() => onDigit(d)}>
          <Text style={styles.keyText}>{d}</Text>
        </Pressable>
      ))}
      <View style={styles.slot}>{rightSlot}</View>
      <Pressable style={keyStyle} onPress={() => onDigit('0')}>
        <Text style={styles.keyText}>0</Text>
      </Pressable>
      <Pressable style={styles.slot} onPress={onBackspace}>
        <Text style={styles.backspaceText}>⌫</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  grid: {flexDirection: 'row', flexWrap: 'wrap', gap: 10},
  keySquare: {
    width: '31%',
    height: 62,
    borderRadius: 18,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  keyCircle: {
    width: '31%',
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  slot: {width: '31%', height: 64, alignItems: 'center', justifyContent: 'center'},
  keyText: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 23},
  backspaceText: {color: colors.textSecondary, fontSize: 22},
});

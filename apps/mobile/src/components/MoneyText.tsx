import React from 'react';
import {StyleProp, StyleSheet, Text, TextStyle} from 'react-native';
import {colors, typography} from '@/theme/tokens';

type Props = {
  amount: number;
  currency?: string;
  positive?: boolean; // tints green
  negative?: boolean; // tints red
  style?: StyleProp<TextStyle>;
};

// Every monetary figure in the app should render through here — it's the
// single place the tabular-figure typography role (DESIGN_BRIEF.md
// "Utility / tabular") and INR formatting live, so amount columns line up
// consistently across wallets/transactions/insights screens.
export function MoneyText({amount, currency = 'INR', positive, negative, style}: Props) {
  const symbol = currency === 'INR' ? '₹' : currency;
  const formatted = Math.abs(amount).toLocaleString('en-IN', {maximumFractionDigits: 2});
  const sign = amount < 0 ? '-' : '';

  return (
    <Text
      style={[
        styles.base,
        positive && {color: colors.positive},
        negative && {color: colors.negative},
        style,
      ]}>
      {sign}
      {symbol}
      {formatted}
    </Text>
  );
}

const styles = StyleSheet.create({
  base: {...typography.monetary, fontVariant: [...typography.monetary.fontVariant], color: colors.textPrimary},
});

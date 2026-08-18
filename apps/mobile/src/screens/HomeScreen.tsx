import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {colors, spacing} from '@/theme/tokens';
import {useAuthStore} from '@/state/authStore';

// Placeholder — the real dashboard (hero net-worth card, quick actions,
// recent transactions, budget widget) is Phase 2 (Core Ledger), not built
// in this pass. See docs/decisions/0004.
export function HomeScreen() {
  const name = useAuthStore((s) => s.name);
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Welcome, {name}</Text>
      <Text style={styles.subtitle}>The ledger dashboard lands with Phase 2.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg, justifyContent: 'center'},
  title: {color: colors.textPrimary, fontSize: 22, fontWeight: '600', marginBottom: spacing.sm},
  subtitle: {color: colors.textSecondary, fontSize: 15},
});

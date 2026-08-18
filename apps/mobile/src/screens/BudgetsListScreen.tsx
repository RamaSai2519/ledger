import React from 'react';
import {FlatList, Pressable, StyleSheet, Text, View} from 'react-native';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {Budget} from '@/api/client';
import {budgetsApi} from '@/api/client';
import {MoneyText} from '@/components/MoneyText';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'BudgetsList'>;

const SCOPE_LABELS: Record<Budget['scope'], string> = {
  category: 'Category',
  wallet: 'Wallet',
  overall: 'Overall (household)',
};

// Color-codes the progress bar/percent as spend approaches or crosses the
// budget's highest configured threshold (DESIGN_BRIEF.md positive/negative
// accents) — green while comfortably under, red once >=100%, accent in
// between so a threshold crossing (e.g. 80%) reads as "getting close"
// rather than already-red.
function progressColor(percent: number, thresholds: number[]): string {
  if (percent >= 100) return colors.negative;
  const nearestThreshold = thresholds[0] ?? 100;
  if (percent >= nearestThreshold) return colors.accent;
  return colors.positive;
}

export function BudgetCard({budget, onPress}: {budget: Budget; onPress: () => void}) {
  const progressQuery = useQuery({
    queryKey: ['budgets', budget.id, 'progress'],
    queryFn: () => budgetsApi.progress(budget.id),
  });

  const percent = progressQuery.data?.percent ?? 0;
  const clampedPercent = Math.min(100, Math.max(0, percent));
  const color = progressColor(percent, budget.threshold_percents);

  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={styles.cardHeader}>
        <Text style={styles.scopeLabel}>{SCOPE_LABELS[budget.scope]}</Text>
        <Text style={[styles.percentText, {color}]}>{percent.toFixed(0)}%</Text>
      </View>
      <View style={styles.barTrack}>
        <View style={[styles.barFill, {width: `${clampedPercent}%`, backgroundColor: color}]} />
      </View>
      <View style={styles.cardFooter}>
        <MoneyText amount={progressQuery.data?.spent ?? 0} style={styles.spentAmount} />
        <Text style={styles.ofAmount}> of </Text>
        <MoneyText amount={budget.amount} style={styles.capAmount} />
      </View>
    </Pressable>
  );
}

export function BudgetsListScreen({navigation}: Props) {
  const query = useQuery({queryKey: ['budgets'], queryFn: () => budgetsApi.list()});
  const queryClient = useQueryClient();

  React.useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      queryClient.invalidateQueries({queryKey: ['budgets']});
    });
    return unsubscribe;
  }, [navigation, queryClient]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Budgets</Text>
        <Pressable style={styles.addButton} onPress={() => navigation.navigate('BudgetForm', undefined)}>
          <Text style={styles.addButtonText}>+ Add</Text>
        </Pressable>
      </View>

      {query.isLoading && <Text style={styles.stateText}>Loading budgets…</Text>}
      {query.isError && <Text style={styles.errorText}>{(query.error as Error).message}</Text>}
      {query.isSuccess && query.data.budgets.length === 0 && (
        <Text style={styles.stateText}>No budgets yet — set a monthly cap on a category, wallet, or overall.</Text>
      )}

      <FlatList
        data={query.data?.budgets ?? []}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{gap: spacing.sm}}
        renderItem={({item}) => (
          <BudgetCard budget={item} onPress={() => navigation.navigate('BudgetForm', {budgetId: item.id})} />
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  header: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg},
  title: {color: colors.textPrimary, fontSize: 22, fontWeight: '600'},
  addButton: {backgroundColor: colors.accent, borderRadius: radius.pill, paddingVertical: spacing.xs, paddingHorizontal: spacing.md},
  addButtonText: {color: colors.textPrimary, fontWeight: '600'},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl},
  errorText: {color: colors.negative, textAlign: 'center', marginTop: spacing.xl},
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
  },
  cardHeader: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm},
  scopeLabel: {color: colors.textPrimary, fontSize: 15, fontWeight: '600'},
  percentText: {fontSize: 14, fontWeight: '700'},
  barTrack: {height: 8, borderRadius: radius.pill, backgroundColor: colors.border, overflow: 'hidden', marginBottom: spacing.sm},
  barFill: {height: '100%', borderRadius: radius.pill},
  cardFooter: {flexDirection: 'row', alignItems: 'baseline'},
  spentAmount: {fontSize: 14},
  ofAmount: {color: colors.textSecondary, fontSize: 13},
  capAmount: {fontSize: 14, color: colors.textSecondary},
});

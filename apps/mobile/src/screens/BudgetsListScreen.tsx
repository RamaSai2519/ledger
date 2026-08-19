import React from 'react';
import {FlatList, Pressable, StyleSheet, Text, View} from 'react-native';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import type {RootStackParamList} from '@/navigation/types';
import type {Budget, Category} from '@/api/client';
import {budgetsApi, categoriesApi} from '@/api/client';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';
import {glyphForCategoryIcon} from '@/theme/categoryIcons';

type Props = NativeStackScreenProps<RootStackParamList, 'BudgetsList'>;

function progressColor(percent: number, thresholds: number[]): string {
  if (percent >= 100) return colors.negative;
  const nearestThreshold = thresholds[0] ?? 100;
  if (percent >= nearestThreshold) return colors.accent;
  return colors.positive;
}

function daysLeftInMonth(): number {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return Math.max(1, end.getDate() - now.getDate());
}

function OverallHeroCard({budget}: {budget: Budget}) {
  const progressQuery = useQuery({queryKey: ['budgets', budget.id, 'progress'], queryFn: () => budgetsApi.progress(budget.id)});
  const spent = progressQuery.data?.spent ?? 0;
  const percent = Math.min(100, progressQuery.data?.percent ?? 0);
  const left = budget.amount - spent;
  const perDay = Math.max(0, left) / daysLeftInMonth();

  return (
    <View style={styles.heroCard}>
      <View style={styles.heroTopRow}>
        <Text style={styles.heroMeta}>Overall, {new Date().toLocaleDateString('en-IN', {month: 'long'})}</Text>
        <Text style={styles.heroMeta}>{daysLeftInMonth()} days left</Text>
      </View>
      <View style={styles.heroAmountRow}>
        <Text style={styles.heroAmount}>₹{spent.toLocaleString('en-IN')}</Text>
        <Text style={styles.heroOf}>of ₹{budget.amount.toLocaleString('en-IN')}</Text>
      </View>
      <View style={styles.heroTrack}>
        <View style={[styles.heroFill, {width: `${percent}%`}]} />
      </View>
      <View style={styles.heroFooterRow}>
        <Text style={[styles.heroFooterText, {color: left >= 0 ? colors.positive : colors.negative}]}>
          ₹{Math.abs(left).toLocaleString('en-IN')} {left >= 0 ? 'left' : 'over'}
        </Text>
        <Text style={styles.heroFooterTextMuted}>₹{perDay.toFixed(0)}/day to stay on track</Text>
      </View>
    </View>
  );
}

function BudgetCard({budget, category, onPress}: {budget: Budget; category?: Category; onPress: () => void}) {
  const progressQuery = useQuery({queryKey: ['budgets', budget.id, 'progress'], queryFn: () => budgetsApi.progress(budget.id)});
  const percent = progressQuery.data?.percent ?? 0;
  const clampedPercent = Math.min(100, Math.max(0, percent));
  const color = progressColor(percent, budget.threshold_percents);
  const over = percent >= 100;
  const label = budget.scope === 'overall' ? 'Overall' : category?.name ?? budget.scope;

  return (
    <Pressable style={[styles.card, over && styles.cardOver]} onPress={onPress}>
      <View style={styles.cardHeader}>
        {budget.scope !== 'overall' && (
          <View style={[styles.cardIconTile, {backgroundColor: `${category?.color ?? colors.accent}24`}]}>
            <MaterialCommunityIcons name={glyphForCategoryIcon(category?.icon)} size={15} color={category?.color ?? colors.accent} />
          </View>
        )}
        <Text style={styles.cardLabel}>{label}</Text>
        <Text style={[styles.cardAmount, over && {color: colors.negative}]}>
          ₹{(progressQuery.data?.spent ?? 0).toLocaleString('en-IN')} <Text style={styles.cardAmountMuted}>/ {budget.amount.toLocaleString('en-IN')}</Text>
        </Text>
      </View>
      <View style={styles.cardTrack}>
        <View style={[styles.cardFill, {width: `${clampedPercent}%`, backgroundColor: color}]} />
      </View>
      {over && (
        <Text style={styles.overText}>
          ₹{((progressQuery.data?.spent ?? 0) - budget.amount).toLocaleString('en-IN')} over. Alerted at{' '}
          {budget.threshold_percents[budget.threshold_percents.length - 1] ?? 100}%.
        </Text>
      )}
    </Pressable>
  );
}

export function BudgetsListScreen({navigation}: Props) {
  const query = useQuery({queryKey: ['budgets'], queryFn: () => budgetsApi.list()});
  const categoriesQuery = useQuery({queryKey: ['categories', 'all'], queryFn: () => categoriesApi.list()});
  const queryClient = useQueryClient();

  React.useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      queryClient.invalidateQueries({queryKey: ['budgets']});
    });
    return unsubscribe;
  }, [navigation, queryClient]);

  const budgets = query.data?.budgets ?? [];
  const overall = budgets.find((b) => b.scope === 'overall');
  const rest = budgets.filter((b) => b.scope !== 'overall');
  const categoryById = new Map((categoriesQuery.data?.categories ?? []).map((c) => [c.id, c]));

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Budgets</Text>
        <Pressable onPress={() => navigation.navigate('BudgetForm', undefined)} hitSlop={8}>
          <MaterialIcons name="add" style={styles.addGlyph} />
        </Pressable>
      </View>

      {query.isLoading && <Text style={styles.stateText}>Loading budgets…</Text>}
      {query.isError && <Text style={styles.errorText}>{(query.error as Error).message}</Text>}
      {query.isSuccess && budgets.length === 0 && (
        <Text style={styles.stateText}>No budgets yet — set a monthly cap on a category, wallet, or overall.</Text>
      )}

      {overall && <OverallHeroCard budget={overall} />}
      {rest.length > 0 && <Text style={styles.sectionLabel}>By category</Text>}

      <FlatList
        data={rest}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{paddingHorizontal: spacing.lg, gap: spacing.sm, paddingBottom: spacing.lg}}
        renderItem={({item}) => (
          <BudgetCard
            budget={item}
            category={item.scope_ref_id ? categoryById.get(item.scope_ref_id) : undefined}
            onPress={() => navigation.navigate('BudgetForm', {budgetId: item.id})}
          />
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  header: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 20, fontWeight: '600'},
  addGlyph: {color: colors.accentOnDark, fontSize: 24},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl, paddingHorizontal: spacing.lg},
  errorText: {color: colors.negative, textAlign: 'center', marginTop: spacing.xl},
  heroCard: {margin: spacing.lg, marginBottom: 0, padding: 18, borderRadius: radius.card, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  heroTopRow: {flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between'},
  heroMeta: {fontSize: 11.5, color: colors.textSecondary},
  heroAmountRow: {flexDirection: 'row', alignItems: 'flex-end', gap: 8, marginTop: spacing.xs},
  heroAmount: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 28, letterSpacing: -0.8, fontWeight: '600'},
  heroOf: {color: colors.textSecondary, fontFamily: fontFamilies.monetary, fontSize: 12.5, paddingBottom: 5},
  heroTrack: {height: 8, borderRadius: 4, backgroundColor: colors.border, overflow: 'hidden', marginTop: spacing.md},
  heroFill: {height: '100%', backgroundColor: colors.accent},
  heroFooterRow: {flexDirection: 'row', justifyContent: 'space-between', marginTop: spacing.sm},
  heroFooterText: {fontFamily: fontFamilies.monetary, fontSize: 11},
  heroFooterTextMuted: {fontFamily: fontFamilies.monetary, fontSize: 11, color: colors.textSecondary},
  sectionLabel: {fontSize: 11, letterSpacing: 1, textTransform: 'uppercase', color: '#5A5A66', paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.sm},
  card: {padding: 14, borderRadius: radius.row, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  cardOver: {borderColor: 'rgba(255,107,107,.32)'},
  cardHeader: {flexDirection: 'row', alignItems: 'center', gap: 10},
  cardIconTile: {width: 26, height: 26, borderRadius: radius.iconTile - 4, alignItems: 'center', justifyContent: 'center'},
  cardLabel: {flex: 1, color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  cardAmount: {fontFamily: fontFamilies.monetary, fontSize: 12.5, color: colors.textPrimary},
  cardAmountMuted: {color: '#73737F'},
  cardTrack: {height: 6, borderRadius: 3, backgroundColor: colors.border, overflow: 'hidden', marginTop: 11},
  cardFill: {height: '100%', borderRadius: 3},
  overText: {fontSize: 11, color: colors.negative, marginTop: spacing.sm},
});

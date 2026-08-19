import React from 'react';
import {Pressable, ScrollView, StyleSheet, Text, View} from 'react-native';
import {useQuery} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {InsightPeriod} from '@/api/client';
import {insightsApi} from '@/api/client';
import {BottomNavBar} from '@/components/BottomNavBar';
import {MoneyText} from '@/components/MoneyText';
import {GroupedSparkline, HorizontalBarList, Sparkline} from '@/components/InsightBars';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'Insights'>;

const PERIODS: InsightPeriod[] = ['daily', 'monthly', 'yearly'];
const PERIOD_LABELS: Record<InsightPeriod, string> = {daily: 'Daily', monthly: 'Monthly', yearly: 'Yearly'};

// Buckets come back as "2026-08-10" (daily), "2026-08" (monthly), or
// "2026" (yearly) — trim to a short axis label so the sparkline stays
// readable at the small width each bar gets.
function shortBucketLabel(period: InsightPeriod, bucket: string): string {
  if (period === 'daily') return bucket.slice(8, 10);
  if (period === 'monthly') {
    const [, month] = bucket.split('-');
    const monthNames = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return monthNames[Number(month)] ?? bucket;
  }
  return bucket;
}

function SectionHeader({title}: {title: string}) {
  return <Text style={styles.sectionTitle}>{title}</Text>;
}

function PeriodToggle({period, onChange}: {period: InsightPeriod; onChange: (p: InsightPeriod) => void}) {
  return (
    <View style={styles.toggleRow}>
      {PERIODS.map((p) => (
        <Pressable
          key={p}
          style={[styles.toggleButton, p === period && styles.toggleButtonActive]}
          onPress={() => onChange(p)}>
          <Text style={[styles.toggleText, p === period && styles.toggleTextActive]}>{PERIOD_LABELS[p]}</Text>
        </Pressable>
      ))}
    </View>
  );
}

function TrendSection({period}: {period: InsightPeriod}) {
  const query = useQuery({queryKey: ['insights', 'trends', period], queryFn: () => insightsApi.trends({period})});
  const total = query.data?.points.reduce((s, p) => s + p.expense, 0) ?? 0;

  return (
    <View style={styles.card}>
      <Text style={styles.totalLabel}>Total spent{period === 'monthly' ? `, ${new Date().toLocaleDateString('en-IN', {month: 'long'})}` : ''}</Text>
      {query.isSuccess && <Text style={styles.totalAmount}>₹{total.toLocaleString('en-IN')}</Text>}
      {query.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {query.isError && <Text style={styles.errorText}>{(query.error as Error).message}</Text>}
      {query.isSuccess && (
        <Sparkline
          color={colors.negative}
          points={query.data.points.map((p) => ({label: shortBucketLabel(period, p.bucket), value: p.expense}))}
        />
      )}
    </View>
  );
}

function IncomeVsExpenseSection({period}: {period: InsightPeriod}) {
  const query = useQuery({
    queryKey: ['insights', 'income-vs-expense', period],
    queryFn: () => insightsApi.incomeVsExpense({period}),
  });

  const totals = query.data?.points.reduce(
    (acc, p) => ({income: acc.income + p.income, expense: acc.expense + p.expense}),
    {income: 0, expense: 0},
  );

  return (
    <View style={styles.card}>
      <SectionHeader title="Income vs expense" />
      {query.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {query.isError && <Text style={styles.errorText}>{(query.error as Error).message}</Text>}
      {query.isSuccess && (
        <>
          <View style={styles.legendRow}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, {backgroundColor: colors.positive}]} />
              <Text style={styles.legendLabel}>Income</Text>
              <MoneyText amount={totals?.income ?? 0} style={styles.legendAmount} />
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, {backgroundColor: colors.negative}]} />
              <Text style={styles.legendLabel}>Expense</Text>
              <MoneyText amount={totals?.expense ?? 0} style={styles.legendAmount} />
            </View>
          </View>
          <GroupedSparkline
            colorA={colors.positive}
            colorB={colors.negative}
            points={query.data.points.map((p) => ({
              label: shortBucketLabel(period, p.bucket),
              a: p.income,
              b: p.expense,
            }))}
          />
        </>
      )}
    </View>
  );
}

function CategoryBreakdownSection({period}: {period: InsightPeriod}) {
  const query = useQuery({
    queryKey: ['insights', 'category-breakdown', period],
    queryFn: () => insightsApi.categoryBreakdown({period}),
  });

  return (
    <View style={styles.card}>
      <SectionHeader title="Category breakdown" />
      {query.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {query.isError && <Text style={styles.errorText}>{(query.error as Error).message}</Text>}
      {query.isSuccess && query.data.items.length === 0 && (
        <Text style={styles.stateText}>No expenses in this period yet.</Text>
      )}
      {query.isSuccess && query.data.items.length > 0 && (
        <HorizontalBarList
          items={query.data.items.slice(0, 8).map((item) => ({
            label: item.category_name,
            value: item.amount,
            color: item.category_color,
            amountLabel: `₹${item.amount.toLocaleString('en-IN', {maximumFractionDigits: 0})}`,
          }))}
        />
      )}
    </View>
  );
}

function NetWorthSection() {
  const query = useQuery({queryKey: ['insights', 'net-worth-history'], queryFn: () => insightsApi.netWorthHistory()});
  const snapshots = query.data?.snapshots ?? [];
  const latest = snapshots[snapshots.length - 1];

  return (
    <View style={styles.card}>
      <SectionHeader title="Net worth over time" />
      {query.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {query.isError && <Text style={styles.errorText}>{(query.error as Error).message}</Text>}
      {query.isSuccess && snapshots.length === 0 && (
        <Text style={styles.stateText}>
          No snapshots yet — the nightly net-worth job populates this once it has run.
        </Text>
      )}
      {query.isSuccess && snapshots.length > 0 && (
        <>
          <MoneyText
            amount={latest?.net_worth ?? 0}
            style={styles.netWorthAmount}
            positive={(latest?.net_worth ?? 0) >= 0}
            negative={(latest?.net_worth ?? 0) < 0}
          />
          <Sparkline
            color={colors.accent}
            points={snapshots.map((s) => ({
              label: s.date ? s.date.slice(8, 10) : '',
              value: s.net_worth,
            }))}
          />
        </>
      )}
    </View>
  );
}

export function InsightsScreen(_props: Props) {
  const [period, setPeriod] = React.useState<InsightPeriod>('monthly');

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Insights</Text>
        <Text style={styles.calendarGlyph}>🗓</Text>
      </View>
      <ScrollView contentContainerStyle={styles.content}>
        <PeriodToggle period={period} onChange={setPeriod} />
        <TrendSection period={period} />
        <IncomeVsExpenseSection period={period} />
        <CategoryBreakdownSection period={period} />
        <NetWorthSection />
      </ScrollView>
      <BottomNavBar active="insights" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  header: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 20, fontWeight: '600'},
  calendarGlyph: {fontSize: 18},
  totalLabel: {fontSize: 11, letterSpacing: 0.8, textTransform: 'uppercase', color: colors.textSecondary},
  totalAmount: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 32, letterSpacing: -1, fontWeight: '600', marginTop: 4},
  content: {padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl},
  toggleRow: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 4,
  },
  toggleButton: {flex: 1, borderRadius: radius.pill, paddingVertical: spacing.xs, alignItems: 'center'},
  toggleButtonActive: {backgroundColor: colors.accent},
  toggleText: {color: colors.textSecondary, fontSize: 13, fontWeight: '600'},
  toggleTextActive: {color: colors.textPrimary},
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    gap: spacing.sm,
  },
  sectionTitle: {color: colors.textPrimary, fontSize: 16, fontWeight: '600'},
  stateText: {color: colors.textSecondary, fontSize: 13},
  errorText: {color: colors.negative, fontSize: 13},
  legendRow: {flexDirection: 'row', gap: spacing.lg},
  legendItem: {flexDirection: 'row', alignItems: 'center', gap: spacing.xs},
  legendDot: {width: 8, height: 8, borderRadius: 4},
  legendLabel: {color: colors.textSecondary, fontSize: 12},
  legendAmount: {fontSize: 12},
  netWorthAmount: {fontSize: 28, fontWeight: '700'},
});

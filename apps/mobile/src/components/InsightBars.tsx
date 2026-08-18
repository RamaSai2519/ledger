import React from 'react';
import {ScrollView, StyleSheet, Text, View} from 'react-native';
import {colors, spacing} from '@/theme/tokens';

// LED-6 note: plan.md calls for a "gradient-filled trend area chart with a
// floating value tooltip on scrub" via react-native-gifted-charts or
// victory-native. Neither is in package.json, and there's no device/
// emulator reliably available here to verify a large new native charting
// dependency actually builds — so this ships a plain, honest bar
// visualization built only from Views, deferring the real gradient/scrub
// chart to a follow-up once a charting library is chosen and validated.

const SPARKLINE_HEIGHT = 64;
const BAR_WIDTH = 10;

function barHeight(value: number, max: number): number {
  if (max <= 0) return 2;
  return Math.max(2, (Math.abs(value) / max) * SPARKLINE_HEIGHT);
}

export type SparklinePoint = {label: string; value: number};

// Single-series bar sparkline — used for the expense trend.
export function Sparkline({points, color}: {points: SparklinePoint[]; color: string}) {
  const max = Math.max(1, ...points.map((p) => Math.abs(p.value)));

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
      {points.map((point, i) => (
        <View key={`${point.label}-${i}`} style={styles.column}>
          <View style={styles.barTrack}>
            <View style={[styles.bar, {height: barHeight(point.value, max), backgroundColor: color}]} />
          </View>
          <Text style={styles.barLabel} numberOfLines={1}>
            {point.label}
          </Text>
        </View>
      ))}
    </ScrollView>
  );
}

export type GroupedSparklinePoint = {label: string; a: number; b: number};

// Two-series bar sparkline (income vs expense) — paired bars per bucket.
export function GroupedSparkline({
  points,
  colorA,
  colorB,
}: {
  points: GroupedSparklinePoint[];
  colorA: string;
  colorB: string;
}) {
  const max = Math.max(1, ...points.map((p) => Math.max(Math.abs(p.a), Math.abs(p.b))));

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
      {points.map((point, i) => (
        <View key={`${point.label}-${i}`} style={styles.column}>
          <View style={styles.groupedBarTrack}>
            <View style={[styles.bar, styles.groupedBar, {height: barHeight(point.a, max), backgroundColor: colorA}]} />
            <View style={[styles.bar, styles.groupedBar, {height: barHeight(point.b, max), backgroundColor: colorB}]} />
          </View>
          <Text style={styles.barLabel} numberOfLines={1}>
            {point.label}
          </Text>
        </View>
      ))}
    </ScrollView>
  );
}

// Horizontal proportional bar list — used for category breakdown, where a
// ranked list reads more clearly than a sparkline.
export function HorizontalBarList({
  items,
}: {
  items: {label: string; value: number; color: string | null; amountLabel: string}[];
}) {
  const max = Math.max(1, ...items.map((i) => i.value));

  return (
    <View style={{gap: spacing.sm}}>
      {items.map((item, i) => (
        <View key={`${item.label}-${i}`}>
          <View style={styles.hBarHeaderRow}>
            <Text style={styles.hBarLabel} numberOfLines={1}>
              {item.label}
            </Text>
            <Text style={styles.hBarAmount}>{item.amountLabel}</Text>
          </View>
          <View style={styles.hBarTrack}>
            <View
              style={[
                styles.hBarFill,
                {width: `${Math.max(2, (item.value / max) * 100)}%`, backgroundColor: item.color ?? colors.accent},
              ]}
            />
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {gap: spacing.sm, alignItems: 'flex-end', paddingVertical: spacing.xs},
  column: {alignItems: 'center', width: 28},
  barTrack: {height: SPARKLINE_HEIGHT, justifyContent: 'flex-end'},
  groupedBarTrack: {height: SPARKLINE_HEIGHT, flexDirection: 'row', alignItems: 'flex-end', gap: 2},
  bar: {width: BAR_WIDTH, borderRadius: 3},
  groupedBar: {width: (BAR_WIDTH - 2) / 2},
  barLabel: {color: colors.textSecondary, fontSize: 9, marginTop: spacing.xs, width: 28, textAlign: 'center'},
  hBarHeaderRow: {flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4},
  hBarLabel: {color: colors.textPrimary, fontSize: 13, fontWeight: '600', flexShrink: 1},
  hBarAmount: {color: colors.textSecondary, fontSize: 12},
  hBarTrack: {height: 8, borderRadius: 4, backgroundColor: colors.border, overflow: 'hidden'},
  hBarFill: {height: '100%', borderRadius: 4},
});

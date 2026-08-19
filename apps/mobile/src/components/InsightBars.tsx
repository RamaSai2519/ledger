import React, {useState} from 'react';
import {LayoutChangeEvent, StyleSheet, Text, View} from 'react-native';
import Svg, {Circle, Defs, LinearGradient, Path, Stop} from 'react-native-svg';
import {colors, fontFamilies, spacing} from '@/theme/tokens';

// LED-10: replaces the flexbox-bar approximation with a real react-native-svg
// gradient area/line chart (smooth curve, highlighted last point + value
// callout), matching the design project's trend charts (e.g.
// `Khaata App.dc.html#s13`, `#s20`).

const CHART_HEIGHT = 88;
const H_PADDING = 6;
const V_PADDING = 14; // headroom for the top callout + bottom labels

// Builds a smoothed SVG path through `points` (screen-space [x, y] pairs)
// using per-segment cubic-bezier control points offset 1/3 of the way along
// each segment — a simple, well-known technique for a natural-looking curve
// without a full Catmull-Rom implementation.
function smoothPath(points: {x: number; y: number}[]): string {
  if (points.length === 0) return '';
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i];
    const p1 = points[i + 1];
    const cx = p0.x + (p1.x - p0.x) / 2;
    d += ` C ${cx} ${p0.y}, ${cx} ${p1.y}, ${p1.x} ${p1.y}`;
  }
  return d;
}

function toScreenPoints(values: number[], width: number, min: number, max: number): {x: number; y: number}[] {
  const usableWidth = Math.max(1, width - H_PADDING * 2);
  const usableHeight = CHART_HEIGHT - V_PADDING * 2;
  const range = Math.max(1e-6, max - min);
  const step = values.length > 1 ? usableWidth / (values.length - 1) : 0;
  return values.map((v, i) => ({
    x: H_PADDING + (values.length > 1 ? i * step : usableWidth / 2),
    y: V_PADDING + usableHeight - ((v - min) / range) * usableHeight,
  }));
}

function useMeasuredWidth(fallback = 280) {
  const [width, setWidth] = useState(fallback);
  const onLayout = (e: LayoutChangeEvent) => {
    const w = e.nativeEvent.layout.width;
    if (w > 0 && Math.abs(w - width) > 1) setWidth(w);
  };
  return {width, onLayout};
}

export type SparklinePoint = {label: string; value: number};

// Single-series gradient area chart — used for the expense trend and net
// worth history.
export function Sparkline({points, color}: {points: SparklinePoint[]; color: string}) {
  const {width, onLayout} = useMeasuredWidth();
  const gradientId = `sparkline-${color.replace('#', '')}`;
  const values = points.map((p) => p.value);
  const min = Math.min(0, ...values);
  const max = Math.max(1, ...values);
  const screenPoints = toScreenPoints(values, width, min, max);
  const linePath = smoothPath(screenPoints);
  const baseline = V_PADDING + (CHART_HEIGHT - V_PADDING * 2);
  const areaPath = screenPoints.length
    ? `${linePath} L ${screenPoints[screenPoints.length - 1].x} ${baseline} L ${screenPoints[0].x} ${baseline} Z`
    : '';
  const last = screenPoints[screenPoints.length - 1];
  const lastValue = points[points.length - 1];

  return (
    <View onLayout={onLayout} style={styles.chartWrap}>
      {width > 0 && points.length > 0 && (
        <Svg width={width} height={CHART_HEIGHT}>
          <Defs>
            <LinearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0" stopColor={color} stopOpacity={0.35} />
              <Stop offset="1" stopColor={color} stopOpacity={0} />
            </LinearGradient>
          </Defs>
          <Path d={areaPath} fill={`url(#${gradientId})`} />
          <Path d={linePath} stroke={color} strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          {last && <Circle cx={last.x} cy={last.y} r={3.5} fill={color} stroke={colors.background} strokeWidth={1.5} />}
        </Svg>
      )}
      {lastValue && last && (
        <View style={[styles.callout, {left: Math.min(Math.max(last.x - 26, 0), width - 52)}]}>
          <Text style={styles.calloutText} numberOfLines={1}>
            {lastValue.value < 0 ? '−' : ''}₹{Math.abs(lastValue.value).toLocaleString('en-IN')}
          </Text>
        </View>
      )}
      <View style={styles.labelRow}>
        {points.map((p, i) => (
          <Text key={`${p.label}-${i}`} style={styles.axisLabel} numberOfLines={1}>
            {p.label}
          </Text>
        ))}
      </View>
    </View>
  );
}

export type GroupedSparklinePoint = {label: string; a: number; b: number};

// Two-series line chart (income vs expense) — series A gets the gradient
// fill (primary), series B is an unfilled accent stroke.
export function GroupedSparkline({
  points,
  colorA,
  colorB,
}: {
  points: GroupedSparklinePoint[];
  colorA: string;
  colorB: string;
}) {
  const {width, onLayout} = useMeasuredWidth();
  const gradientId = `grouped-sparkline-${colorA.replace('#', '')}`;
  const valuesA = points.map((p) => p.a);
  const valuesB = points.map((p) => p.b);
  const min = Math.min(0, ...valuesA, ...valuesB);
  const max = Math.max(1, ...valuesA, ...valuesB);
  const screenA = toScreenPoints(valuesA, width, min, max);
  const screenB = toScreenPoints(valuesB, width, min, max);
  const lineA = smoothPath(screenA);
  const lineB = smoothPath(screenB);
  const baseline = V_PADDING + (CHART_HEIGHT - V_PADDING * 2);
  const areaA = screenA.length
    ? `${lineA} L ${screenA[screenA.length - 1].x} ${baseline} L ${screenA[0].x} ${baseline} Z`
    : '';
  const lastA = screenA[screenA.length - 1];
  const lastB = screenB[screenB.length - 1];

  return (
    <View onLayout={onLayout} style={styles.chartWrap}>
      {width > 0 && points.length > 0 && (
        <Svg width={width} height={CHART_HEIGHT}>
          <Defs>
            <LinearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0" stopColor={colorA} stopOpacity={0.3} />
              <Stop offset="1" stopColor={colorA} stopOpacity={0} />
            </LinearGradient>
          </Defs>
          <Path d={areaA} fill={`url(#${gradientId})`} />
          <Path d={lineB} stroke={colorB} strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="4 3" />
          <Path d={lineA} stroke={colorA} strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          {lastA && <Circle cx={lastA.x} cy={lastA.y} r={3.5} fill={colorA} stroke={colors.background} strokeWidth={1.5} />}
          {lastB && <Circle cx={lastB.x} cy={lastB.y} r={3} fill={colorB} stroke={colors.background} strokeWidth={1.5} />}
        </Svg>
      )}
      <View style={styles.labelRow}>
        {points.map((p, i) => (
          <Text key={`${p.label}-${i}`} style={styles.axisLabel} numberOfLines={1}>
            {p.label}
          </Text>
        ))}
      </View>
    </View>
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
  chartWrap: {width: '100%'},
  labelRow: {flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: H_PADDING, marginTop: 2},
  axisLabel: {color: colors.textSecondary, fontSize: 9, flexShrink: 1},
  callout: {position: 'absolute', top: 0, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  calloutText: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 9.5},
  hBarHeaderRow: {flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4},
  hBarLabel: {color: colors.textPrimary, fontSize: 13, fontWeight: '600', flexShrink: 1},
  hBarAmount: {color: colors.textSecondary, fontSize: 12},
  hBarTrack: {height: 8, borderRadius: 4, backgroundColor: colors.border, overflow: 'hidden'},
  hBarFill: {height: '100%', borderRadius: 4},
});

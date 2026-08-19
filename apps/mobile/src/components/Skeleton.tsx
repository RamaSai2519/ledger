import React, {useEffect, useRef} from 'react';
import {Animated, StyleSheet, View} from 'react-native';
import type {StyleProp, ViewStyle} from 'react-native';
import {colors, motion, radius} from '@/theme/tokens';

// Shared shimmer block for every screen's loading state (spec1 "Motion":
// "Skeletons shimmer 1.6s linear") — a single opacity pulse loop, reused
// instead of each screen building its own Animated.Value.
export function Skeleton({style, radius: r = radius.row}: {style?: StyleProp<ViewStyle>; radius?: number}) {
  const opacity = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {toValue: 1, duration: motion.skeletonShimmerMs / 2, useNativeDriver: true}),
        Animated.timing(opacity, {toValue: 0.4, duration: motion.skeletonShimmerMs / 2, useNativeDriver: true}),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [opacity]);

  return <Animated.View style={[styles.base, {borderRadius: r, opacity}, style]} />;
}

// A row of shimmer blocks shaped like a list row (icon tile + two text
// lines + trailing amount) — the most common loading-state shape across
// Home/Wallets/Insights/Transactions.
export function SkeletonRow({style}: {style?: StyleProp<ViewStyle>}) {
  return (
    <View style={[styles.row, style]}>
      <Skeleton style={styles.rowIcon} radius={radius.iconTile} />
      <View style={styles.rowLines}>
        <Skeleton style={styles.lineWide} />
        <Skeleton style={styles.lineNarrow} />
      </View>
      <Skeleton style={styles.rowAmount} />
    </View>
  );
}

const styles = StyleSheet.create({
  base: {backgroundColor: colors.surface},
  row: {flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 9},
  rowIcon: {width: 36, height: 36},
  rowLines: {flex: 1, gap: 6},
  lineWide: {height: 12, width: '55%'},
  lineNarrow: {height: 10, width: '35%'},
  rowAmount: {width: 50, height: 13},
});

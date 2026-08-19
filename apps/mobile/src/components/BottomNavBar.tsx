import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '@/navigation/types';
import { colors } from '@/theme/tokens';

type Tab = 'home' | 'wallets' | 'insights' | 'settings';

const TABS: Array<{ key: Tab; label: string; glyph: string; route: keyof RootStackParamList }> = [
  { key: 'home', label: 'Home', glyph: '⌂', route: 'Home' },
  { key: 'wallets', label: 'Wallets', glyph: '◧', route: 'WalletsList' },
  { key: 'insights', label: 'Insights', glyph: '◔', route: 'Insights' },
  { key: 'settings', label: 'Settings', glyph: '⚙', route: 'Settings' },
];

// KhaataNav.dc.html in the design project — a persistent bottom tab bar
// (Home / Wallets / center "+" / Insights / Settings) that every core-app
// screen renders. There's no @react-navigation/bottom-tabs dependency
// installed, so this is a plain component rendered at the bottom of each
// of those four screens rather than a real tab navigator — `navigation.navigate`
// on a native-stack still pops back to an existing route instance instead
// of stacking a duplicate, so switching tabs behaves close enough to real
// tabs without adding a new native dependency.
export function BottomNavBar({ active }: { active: Tab }) {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

  return (
    <View style={styles.bar}>
      {TABS.slice(0, 2).map((tab) => (
        <Pressable key={tab.key} style={styles.tab} onPress={() => navigation.navigate(tab.route as never)}>
          <Text style={[styles.glyph, active === tab.key && styles.glyphActive]}>{tab.glyph}</Text>
          <Text style={[styles.label, active === tab.key && styles.labelActive]}>{tab.label}</Text>
        </Pressable>
      ))}
      <View style={styles.fabSpacer} />
      {TABS.slice(2).map((tab) => (
        <Pressable key={tab.key} style={styles.tab} onPress={() => navigation.navigate(tab.route as never)}>
          <Text style={[styles.glyph, active === tab.key && styles.glyphActive]}>{tab.glyph}</Text>
          <Text style={[styles.label, active === tab.key && styles.labelActive]}>{tab.label}</Text>
        </Pressable>
      ))}
      <View style={styles.fabWrap} pointerEvents="box-none">
        <Pressable style={styles.fab} onPress={() => navigation.navigate('TransactionForm', undefined)}>
          <Text style={styles.fabGlyph}>+</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    position: 'relative',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 26,
    paddingTop: 10,
    paddingBottom: 14,
    backgroundColor: colors.backgroundRaised,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  tab: { alignItems: 'center', gap: 3, width: 52 },
  fabSpacer: { width: 56 },
  glyph: { fontSize: 20, color: '#5A5A66' },
  glyphActive: { color: colors.textPrimary },
  label: { fontSize: 9.5, color: '#5A5A66' },
  labelActive: { color: colors.textPrimary },
  fabWrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: -22,
    alignItems: 'center',
  },
  fab: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.accent,
    borderWidth: 4,
    borderColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fabGlyph: { fontSize: 26, color: '#fff', lineHeight: 28 },
});

import React from 'react';
import {Pressable, StyleSheet, Text, View} from 'react-native';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = {
  active: 'create' | 'join';
  onSelectCreate?: () => void;
  onSelectJoin?: () => void;
};

// Segmented Create/Join control shared by HouseholdCreateScreen and
// HouseholdJoinScreen (s06/s07) — the design project shows these as one
// screen with a tab toggle rather than a separate "choose" screen, so each
// route renders this at the top and switching tabs navigates to the other
// route.
export function HouseholdTabs({active, onSelectCreate, onSelectJoin}: Props) {
  return (
    <View style={styles.row}>
      <Pressable
        style={[styles.tab, active === 'create' && styles.tabActive]}
        onPress={onSelectCreate}
        disabled={active === 'create'}>
        <Text style={active === 'create' ? styles.tabTextActive : styles.tabText}>Create</Text>
      </Pressable>
      <Pressable style={[styles.tab, active === 'join' && styles.tabActive]} onPress={onSelectJoin} disabled={active === 'join'}>
        <Text style={active === 'join' ? styles.tabTextActive : styles.tabText}>Join</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', gap: spacing.sm, marginTop: spacing.lg},
  tab: {
    flex: 1,
    height: 42,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabActive: {backgroundColor: colors.surface, borderColor: colors.accent},
  tabText: {fontSize: 12.5, color: colors.textSecondary},
  tabTextActive: {fontSize: 12.5, fontWeight: '600', color: colors.textPrimary},
});

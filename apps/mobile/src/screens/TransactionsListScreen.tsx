import React, {useState} from 'react';
import {Modal, Pressable, ScrollView, StyleSheet, Text, View} from 'react-native';
import {useQuery} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {categoriesApi, transactionsApi, walletsApi} from '@/api/client';
import {PickerField} from '@/components/PickerField';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'TransactionsList'>;

function groupByDay(items: import('@/api/client').Transaction[]) {
  const groups = new Map<string, import('@/api/client').Transaction[]>();
  for (const txn of items) {
    const d = new Date(txn.date);
    const today = new Date();
    const label =
      d.toDateString() === today.toDateString() ? 'Today' : d.toLocaleDateString('en-GB', {day: '2-digit', month: 'long'});
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label)!.push(txn);
  }
  return Array.from(groups.entries());
}

export function TransactionsListScreen({navigation}: Props) {
  const [walletId, setWalletId] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);

  const walletsQuery = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});
  const categoriesQuery = useQuery({queryKey: ['categories', 'all'], queryFn: () => categoriesApi.list()});
  const transactionsQuery = useQuery({
    queryKey: ['transactions', 'list', {walletId, categoryId}],
    queryFn: () =>
      transactionsApi.list({
        wallet_id: walletId ?? undefined,
        category_id: categoryId ?? undefined,
        page_size: 100,
      }),
  });

  const items = transactionsQuery.data?.transactions ?? [];
  const total = items.filter((t) => t.type === 'expense').reduce((s, t) => s + t.amount, 0);
  const groups = groupByDay(items);
  const categoryName = new Map((categoriesQuery.data?.categories ?? []).map((c) => [c.id, c.name]));
  const categoryColor = new Map((categoriesQuery.data?.categories ?? []).map((c) => [c.id, c.color ?? colors.accent]));
  const walletName = new Map((walletsQuery.data?.wallets ?? []).map((w) => [w.id, w.name]));

  const walletOptions = (walletsQuery.data?.wallets ?? []).map((w) => ({label: w.name, value: w.id}));
  const categoryOptions = (categoriesQuery.data?.categories ?? []).map((c) => ({label: c.name, value: c.id}));

  const activeFilters = [
    walletId ? {key: 'wallet', label: walletName.get(walletId) ?? 'Wallet', clear: () => setWalletId(null)} : null,
    categoryId ? {key: 'category', label: categoryName.get(categoryId) ?? 'Category', clear: () => setCategoryId(null)} : null,
  ].filter(Boolean) as Array<{key: string; label: string; clear: () => void}>;

  return (
    <View style={styles.container}>
      {activeFilters.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
          {activeFilters.map((f) => (
            <Pressable key={f.key} style={styles.filterChip} onPress={f.clear}>
              <Text style={styles.filterChipText}>{f.label}</Text>
              <Text style={styles.filterChipClose}>✕</Text>
            </Pressable>
          ))}
          <Pressable
            style={styles.clearChip}
            onPress={() => {
              setWalletId(null);
              setCategoryId(null);
            }}>
            <Text style={styles.clearChipText}>Clear</Text>
          </Pressable>
        </ScrollView>
      )}

      <View style={styles.summaryRow}>
        <Text style={styles.summaryText}>{items.length} matches</Text>
        <Text style={styles.summaryAmount}>−₹{total.toLocaleString('en-IN')}</Text>
      </View>

      {transactionsQuery.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {transactionsQuery.isSuccess && items.length === 0 && <Text style={styles.stateText}>No transactions match these filters.</Text>}

      <ScrollView contentContainerStyle={{paddingHorizontal: spacing.lg, paddingBottom: spacing.xl}}>
        {groups.map(([label, txns]) => (
          <View key={label}>
            <Text style={styles.groupLabel}>{label}</Text>
            {txns.map((txn) => (
              <Pressable key={txn.id} style={styles.row} onPress={() => navigation.navigate('TransactionForm', {transactionId: txn.id})}>
                <View style={[styles.stripe, {backgroundColor: (txn.category_id && categoryColor.get(txn.category_id)) || colors.accent}]} />
                <View style={{flex: 1}}>
                  <Text style={styles.rowMerchant}>{txn.merchant_name || txn.note || txn.type}</Text>
                  <Text style={styles.rowMeta}>
                    {(txn.category_id && categoryName.get(txn.category_id)) || txn.type} · {walletName.get(txn.wallet_id) ?? ''}
                  </Text>
                </View>
                <Text style={styles.rowAmount}>
                  {txn.type === 'expense' ? '−' : txn.type === 'income' ? '+' : ''}₹{txn.amount.toLocaleString('en-IN')}
                </Text>
              </Pressable>
            ))}
          </View>
        ))}
      </ScrollView>

      <Modal visible={filterOpen} transparent animationType="slide" onRequestClose={() => setFilterOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setFilterOpen(false)}>
          <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
            <Text style={styles.sheetTitle}>Filter transactions</Text>
            <PickerField label="Wallet" options={walletOptions} value={walletId} onChange={setWalletId} />
            <PickerField label="Category" options={categoryOptions} value={categoryId} onChange={setCategoryId} />
            <Pressable style={styles.applyButton} onPress={() => setFilterOpen(false)}>
              <Text style={styles.applyButtonText}>Apply filters</Text>
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>

      <Pressable style={styles.filterFab} onPress={() => setFilterOpen(true)}>
        <Text style={styles.filterFabGlyph}>⚙</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  filterRow: {flexDirection: 'row', gap: 7, paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  filterChip: {flexDirection: 'row', alignItems: 'center', gap: 6, paddingLeft: 12, paddingRight: 10, paddingVertical: 6, borderRadius: radius.pill, backgroundColor: colors.textPrimary},
  filterChipText: {color: colors.background, fontSize: 11.5, fontWeight: '600'},
  filterChipClose: {color: colors.background, fontSize: 10},
  clearChip: {paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border},
  clearChipText: {color: colors.textSecondary, fontSize: 11.5},
  summaryRow: {flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  summaryText: {color: colors.textSecondary, fontSize: 11.5},
  summaryAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 14},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl},
  groupLabel: {fontSize: 11, letterSpacing: 1, textTransform: 'uppercase', color: '#5A5A66', paddingTop: spacing.md, paddingBottom: 4},
  row: {flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 9, borderBottomWidth: 1, borderBottomColor: '#17171F'},
  stripe: {width: 3, height: 32, borderRadius: 2},
  rowMerchant: {color: colors.textPrimary, fontSize: 13, fontWeight: '500'},
  rowMeta: {color: colors.textSecondary, fontSize: 11, marginTop: 2},
  rowAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 13.5},
  backdrop: {flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end'},
  sheet: {backgroundColor: colors.backgroundRaised, borderTopLeftRadius: radius.sheet, borderTopRightRadius: radius.sheet, padding: spacing.lg, borderWidth: 1, borderColor: colors.border, borderBottomWidth: 0},
  sheetTitle: {color: colors.textPrimary, fontSize: 16, fontWeight: '600', marginBottom: spacing.md},
  applyButton: {height: 48, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center', marginTop: spacing.sm},
  applyButtonText: {color: colors.textPrimary, fontWeight: '600'},
  filterFab: {
    position: 'absolute',
    right: spacing.lg,
    bottom: spacing.lg,
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterFabGlyph: {color: '#fff', fontSize: 18},
});

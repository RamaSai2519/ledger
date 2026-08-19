import React from 'react';
import {Pressable, ScrollView, StyleSheet, Text, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {categoriesApi, transactionsApi, walletsApi} from '@/api/client';
import {Sparkline} from '@/components/InsightBars';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'WalletDetail'>;

const LIABILITY_TYPES = new Set(['credit_card', 'pay_later', 'loan']);
const CATEGORY_COLORS = [colors.accent, '#E8A33D', '#7FE3B8', '#8FB4FF', '#D4A5FF'];

export function WalletDetailScreen({route, navigation}: Props) {
  const {walletId} = route.params;
  const queryClient = useQueryClient();

  const walletQuery = useQuery({queryKey: ['wallets', walletId], queryFn: () => walletsApi.get(walletId)});
  const historyQuery = useQuery({
    queryKey: ['wallets', walletId, 'balance-history'],
    queryFn: () => walletsApi.balanceHistory(walletId),
  });
  const transactionsQuery = useQuery({
    queryKey: ['transactions', {wallet_id: walletId}],
    queryFn: () => transactionsApi.list({wallet_id: walletId, page_size: 10}),
  });
  const categoriesQuery = useQuery({queryKey: ['categories', 'all'], queryFn: () => categoriesApi.list()});

  const archiveMutation = useMutation({
    mutationFn: () => walletsApi.archive(walletId),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['wallets']});
      navigation.goBack();
    },
  });

  if (walletQuery.isLoading) {
    return (
      <View style={styles.container}>
        <Text style={styles.stateText}>Loading wallet…</Text>
      </View>
    );
  }

  if (walletQuery.isError || !walletQuery.data) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>{(walletQuery.error as Error)?.message ?? 'Wallet not found'}</Text>
      </View>
    );
  }

  const wallet = walletQuery.data;
  const isLiability = LIABILITY_TYPES.has(wallet.type);
  const points = historyQuery.data?.points.slice(-8) ?? [];
  const categoryColor = new Map(
    (categoriesQuery.data?.categories ?? []).map((c, i) => [c.id, c.color ?? CATEGORY_COLORS[i % CATEGORY_COLORS.length]]),
  );
  const categoryName = new Map((categoriesQuery.data?.categories ?? []).map((c) => [c.id, c.name]));

  return (
    <ScrollView style={styles.container} contentContainerStyle={{paddingBottom: spacing.xl}}>
      <View style={styles.heroCard}>
        <View style={styles.heroHeader}>
          <Text style={styles.heroName}>{wallet.name}</Text>
          <View style={styles.heroBadge}>
            <Text style={styles.heroBadgeText}>{isLiability ? 'Owe' : 'Have'}</Text>
          </View>
        </View>
        {!!wallet.account_last4 && <Text style={styles.heroDigits}>•••• •••• {wallet.account_last4}</Text>}
        <View style={styles.heroFooter}>
          <View>
            <Text style={styles.heroLabel}>{isLiability ? 'Outstanding' : 'Available balance'}</Text>
            <Text style={styles.heroAmount}>₹{Math.abs(wallet.current_balance).toLocaleString('en-IN')}</Text>
          </View>
          {isLiability && wallet.credit_card_details?.due_day != null && (
            <View style={{alignItems: 'flex-end'}}>
              <Text style={styles.heroLabel}>Due day</Text>
              <Text style={[styles.heroAmount, {fontSize: 12}]}>{wallet.credit_card_details.due_day}</Text>
            </View>
          )}
        </View>
      </View>

      <View style={styles.actionsRow}>
        <Pressable style={styles.actionButton} onPress={() => navigation.navigate('WalletReconcile', {walletId: wallet.id})}>
          <Text style={styles.actionButtonText}>Reconcile balance</Text>
        </Pressable>
        <Pressable style={styles.actionButton} onPress={() => navigation.navigate('TransactionForm', {walletId: wallet.id})}>
          <Text style={styles.actionButtonText}>Add transaction</Text>
        </Pressable>
      </View>

      <View style={styles.chartCard}>
        <Text style={styles.chartLabel}>Balance history</Text>
        {historyQuery.isLoading && <Text style={styles.stateText}>Loading history…</Text>}
        {historyQuery.isSuccess && points.length === 0 && <Text style={styles.stateText}>No history yet.</Text>}
        {points.length > 0 && (
          <View style={{marginTop: spacing.sm}}>
            <Sparkline
              color={isLiability ? colors.negative : colors.accent}
              points={points.map((p) => ({label: p.label, value: Math.abs(p.balance)}))}
            />
          </View>
        )}
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Transactions</Text>
        <Pressable onPress={() => navigation.navigate('TransactionsList')}>
          <Text style={styles.sectionLink}>See all</Text>
        </Pressable>
      </View>
      {transactionsQuery.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {transactionsQuery.isSuccess && transactionsQuery.data.transactions.length === 0 && (
        <Text style={styles.stateText}>No transactions on this wallet yet.</Text>
      )}
      <View>
        {(transactionsQuery.data?.transactions ?? []).map((txn) => (
          <Pressable
            key={txn.id}
            style={styles.txnRow}
            onPress={() => navigation.navigate('TransactionForm', {transactionId: txn.id})}>
            <View style={[styles.txnStripe, {backgroundColor: (txn.category_id && categoryColor.get(txn.category_id)) || colors.accent}]} />
            <View style={{flex: 1}}>
              <Text style={styles.txnMerchant}>{txn.merchant_name || txn.note || txn.type}</Text>
              <Text style={styles.txnMeta}>
                {(txn.category_id && categoryName.get(txn.category_id)) || txn.type} · {new Date(txn.date).toLocaleDateString()}
              </Text>
            </View>
            <Text style={styles.txnAmount}>
              {txn.type === 'expense' ? '−' : txn.type === 'income' ? '+' : ''}₹{txn.amount.toLocaleString('en-IN')}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.footerActions}>
        <Pressable onPress={() => navigation.navigate('WalletForm', {walletId: wallet.id})}>
          <Text style={styles.footerLink}>Edit wallet</Text>
        </Pressable>
        <Pressable onPress={() => archiveMutation.mutate()} disabled={archiveMutation.isPending}>
          <Text style={styles.archiveButtonText}>{archiveMutation.isPending ? 'Archiving…' : 'Archive wallet'}</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl},
  errorText: {color: colors.negative, textAlign: 'center', marginTop: spacing.xl},
  heroCard: {padding: 18, borderRadius: radius.card, backgroundColor: colors.accent},
  heroHeader: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'},
  heroName: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  heroBadge: {paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.pill, backgroundColor: 'rgba(255,255,255,.16)'},
  heroBadgeText: {color: colors.textPrimary, fontSize: 10},
  heroDigits: {color: 'rgba(255,255,255,.72)', fontFamily: fontFamilies.monetary, fontSize: 13, letterSpacing: 2.5, marginTop: 14},
  heroFooter: {flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', marginTop: 10},
  heroLabel: {color: 'rgba(255,255,255,.62)', fontSize: 10},
  heroAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 22, fontWeight: '500'},
  actionsRow: {flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md},
  actionButton: {flex: 1, height: 42, borderRadius: radius.pill, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center'},
  actionButtonText: {color: colors.textPrimary, fontSize: 12.5, fontWeight: '600'},
  chartCard: {marginTop: spacing.lg, padding: 16, borderRadius: radius.card - 2, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  chartLabel: {fontSize: 12, color: colors.textSecondary},
  sectionHeader: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: spacing.lg, marginBottom: spacing.sm},
  sectionTitle: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 14, fontWeight: '600'},
  sectionLink: {color: colors.textSecondary, fontSize: 11.5},
  txnRow: {flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#17171F'},
  txnStripe: {width: 3, height: 30, borderRadius: 2},
  txnMerchant: {color: colors.textPrimary, fontSize: 13, fontWeight: '500'},
  txnMeta: {color: colors.textSecondary, fontSize: 11, marginTop: 2},
  txnAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 13.5},
  footerActions: {marginTop: spacing.xl, alignItems: 'center', gap: spacing.md},
  footerLink: {color: colors.accentOnDark, fontSize: 13, fontWeight: '600'},
  archiveButtonText: {color: colors.negative, fontSize: 14},
});

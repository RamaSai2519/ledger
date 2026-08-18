import React from 'react';
import {FlatList, Pressable, StyleSheet, Text, View} from 'react-native';
import {useQuery} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {Wallet} from '@/api/client';
import {transactionsApi, walletsApi} from '@/api/client';
import {MoneyText} from '@/components/MoneyText';
import {usePartnerAccent} from '@/hooks/usePartnerAccent';
import {useAuthStore} from '@/state/authStore';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

const LIABILITY_TYPES = new Set<Wallet['type']>(['credit_card', 'pay_later', 'loan']);

function computeNetWorth(wallets: Wallet[]): number {
  return wallets.reduce((sum, w) => {
    if (w.is_archived) return sum;
    return LIABILITY_TYPES.has(w.type) ? sum - w.current_balance : sum + w.current_balance;
  }, 0);
}

function TransactionRow({txn}: {txn: import('@/api/client').Transaction}) {
  const accent = usePartnerAccent(txn.user_id);
  const isExpense = txn.type === 'expense';
  return (
    <View style={[styles.txnRow, {borderLeftColor: accent}]}>
      <View style={{flex: 1}}>
        <Text style={styles.txnMerchant}>{txn.merchant_name || txn.note || txn.type}</Text>
        <Text style={styles.txnDate}>{new Date(txn.date).toLocaleDateString()}</Text>
      </View>
      <MoneyText
        amount={txn.amount}
        positive={txn.type === 'income'}
        negative={isExpense}
        style={styles.txnAmount}
      />
    </View>
  );
}

export function HomeScreen({navigation}: Props) {
  const name = useAuthStore((s) => s.name);

  const walletsQuery = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});
  const transactionsQuery = useQuery({
    queryKey: ['transactions', 'recent'],
    queryFn: () => transactionsApi.list({page: 1, page_size: 10}),
  });

  const netWorth = walletsQuery.data ? computeNetWorth(walletsQuery.data.wallets) : 0;

  return (
    <View style={styles.container}>
      <Text style={styles.greeting}>Welcome, {name}</Text>

      <View style={styles.heroCard}>
        <Text style={styles.heroLabel}>Net worth</Text>
        {walletsQuery.isLoading ? (
          <Text style={styles.stateText}>Loading…</Text>
        ) : (
          <MoneyText amount={netWorth} style={styles.heroAmount} positive={netWorth >= 0} negative={netWorth < 0} />
        )}
      </View>

      <View style={styles.quickActions}>
        <Pressable style={styles.quickAction} onPress={() => navigation.navigate('TransactionForm', undefined)}>
          <Text style={styles.quickActionText}>+ Add transaction</Text>
        </Pressable>
        <Pressable style={styles.quickAction} onPress={() => navigation.navigate('WalletForm', undefined)}>
          <Text style={styles.quickActionText}>+ Add wallet</Text>
        </Pressable>
      </View>

      <View style={styles.linksRow}>
        <Pressable onPress={() => navigation.navigate('WalletsList')}>
          <Text style={styles.link}>Wallets</Text>
        </Pressable>
        <Pressable onPress={() => navigation.navigate('Categories')}>
          <Text style={styles.link}>Categories</Text>
        </Pressable>
      </View>

      <Text style={styles.sectionTitle}>Recent transactions</Text>
      {transactionsQuery.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {transactionsQuery.isSuccess && transactionsQuery.data.transactions.length === 0 && (
        <Text style={styles.stateText}>No transactions yet — add your first one above.</Text>
      )}
      <FlatList
        data={transactionsQuery.data?.transactions ?? []}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{gap: spacing.xs}}
        renderItem={({item}) => (
          <Pressable onPress={() => navigation.navigate('TransactionForm', {transactionId: item.id})}>
            <TransactionRow txn={item} />
          </Pressable>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  greeting: {color: colors.textPrimary, fontSize: 18, fontWeight: '600', marginBottom: spacing.md},
  heroCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  heroLabel: {color: colors.textSecondary, fontSize: 13, marginBottom: spacing.xs},
  heroAmount: {fontSize: 34, fontWeight: '700'},
  stateText: {color: colors.textSecondary, fontSize: 13},
  quickActions: {flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md},
  quickAction: {
    flex: 1,
    backgroundColor: colors.accent,
    borderRadius: radius.pill,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  quickActionText: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  linksRow: {flexDirection: 'row', gap: spacing.lg, marginBottom: spacing.lg},
  link: {color: colors.accent, fontSize: 14, fontWeight: '600'},
  sectionTitle: {color: colors.textPrimary, fontSize: 16, fontWeight: '600', marginBottom: spacing.sm},
  txnRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderLeftWidth: 3,
    padding: spacing.sm,
  },
  txnMerchant: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  txnDate: {color: colors.textSecondary, fontSize: 12, marginTop: 2},
  txnAmount: {fontSize: 14},
});

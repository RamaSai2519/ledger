import React from 'react';
import {Pressable, ScrollView, StyleSheet, Text, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {walletsApi} from '@/api/client';
import {MoneyText} from '@/components/MoneyText';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'WalletDetail'>;

const LIABILITY_TYPES = new Set(['credit_card', 'pay_later', 'loan']);

export function WalletDetailScreen({route, navigation}: Props) {
  const {walletId} = route.params;
  const queryClient = useQueryClient();

  const walletQuery = useQuery({queryKey: ['wallets', walletId], queryFn: () => walletsApi.get(walletId)});
  const historyQuery = useQuery({
    queryKey: ['wallets', walletId, 'balance-history'],
    queryFn: () => walletsApi.balanceHistory(walletId),
  });

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
  const points = historyQuery.data?.points ?? [];
  const maxBalance = Math.max(1, ...points.map((p) => Math.abs(p.balance)));

  return (
    <ScrollView style={styles.container} contentContainerStyle={{paddingBottom: spacing.xl}}>
      <Text style={styles.walletName}>{wallet.name}</Text>
      {wallet.provider && <Text style={styles.provider}>{wallet.provider}</Text>}

      <MoneyText
        amount={wallet.current_balance}
        negative={isLiability && wallet.current_balance > 0}
        positive={!isLiability}
        style={styles.balance}
      />
      <Text style={styles.balanceLabel}>{isLiability ? 'Amount owed' : 'Available balance'}</Text>

      <View style={styles.actionsRow}>
        <Pressable
          style={styles.actionButton}
          onPress={() => navigation.navigate('TransactionForm', {walletId: wallet.id})}>
          <Text style={styles.actionButtonText}>Add transaction</Text>
        </Pressable>
        <Pressable
          style={styles.actionButton}
          onPress={() => navigation.navigate('WalletReconcile', {walletId: wallet.id})}>
          <Text style={styles.actionButtonText}>Reconcile</Text>
        </Pressable>
        <Pressable
          style={styles.actionButton}
          onPress={() => navigation.navigate('WalletForm', {walletId: wallet.id})}>
          <Text style={styles.actionButtonText}>Edit</Text>
        </Pressable>
      </View>

      <Text style={styles.sectionTitle}>Balance history</Text>
      {/* Simple point list with proportional bars — a real chart library
          arrives with Insights (LED-6); this is enough for a wallet-detail
          glance in the meantime. */}
      {historyQuery.isLoading && <Text style={styles.stateText}>Loading history…</Text>}
      {historyQuery.isSuccess && points.length === 0 && <Text style={styles.stateText}>No history yet.</Text>}
      <View style={{gap: spacing.xs}}>
        {points.map((point, index) => (
          <View key={`${point.transaction_id ?? 'opening'}-${index}`} style={styles.historyRow}>
            <View style={styles.barTrack}>
              <View
                style={[
                  styles.barFill,
                  {width: `${(Math.abs(point.balance) / maxBalance) * 100}%`},
                ]}
              />
            </View>
            <MoneyText amount={point.balance} style={styles.historyAmount} />
          </View>
        ))}
      </View>

      <Pressable style={styles.archiveButton} onPress={() => archiveMutation.mutate()} disabled={archiveMutation.isPending}>
        <Text style={styles.archiveButtonText}>
          {archiveMutation.isPending ? 'Archiving…' : 'Archive wallet'}
        </Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl},
  errorText: {color: colors.negative, textAlign: 'center', marginTop: spacing.xl},
  walletName: {color: colors.textPrimary, fontSize: 20, fontWeight: '600'},
  provider: {color: colors.textSecondary, fontSize: 13, marginTop: 2},
  balance: {fontSize: 32, marginTop: spacing.md},
  balanceLabel: {color: colors.textSecondary, fontSize: 13, marginBottom: spacing.lg},
  actionsRow: {flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.lg},
  actionButton: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  actionButtonText: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  sectionTitle: {color: colors.textPrimary, fontSize: 16, fontWeight: '600', marginBottom: spacing.sm},
  historyRow: {flexDirection: 'row', alignItems: 'center', gap: spacing.sm},
  barTrack: {flex: 1, height: 6, borderRadius: 3, backgroundColor: colors.border, overflow: 'hidden'},
  barFill: {height: 6, borderRadius: 3, backgroundColor: colors.accent},
  historyAmount: {fontSize: 13, minWidth: 90, textAlign: 'right'},
  archiveButton: {marginTop: spacing.xl, alignItems: 'center', padding: spacing.sm},
  archiveButtonText: {color: colors.negative, fontSize: 14},
});

import React from 'react';
import {FlatList, Pressable, StyleSheet, Text, View} from 'react-native';
import {useQuery} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {Wallet} from '@/api/client';
import {walletsApi} from '@/api/client';
import {MoneyText} from '@/components/MoneyText';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'WalletsList'>;

const WALLET_TYPE_LABELS: Record<Wallet['type'], string> = {
  bank_account: 'Bank account',
  credit_card: 'Credit card',
  pay_later: 'Pay later',
  cash: 'Cash',
  loan: 'Loan',
};

const LIABILITY_TYPES = new Set<Wallet['type']>(['credit_card', 'pay_later', 'loan']);

export function WalletsListScreen({navigation}: Props) {
  const query = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Wallets</Text>
        <Pressable style={styles.addButton} onPress={() => navigation.navigate('WalletForm', undefined)}>
          <Text style={styles.addButtonText}>+ Add</Text>
        </Pressable>
      </View>

      {query.isLoading && <Text style={styles.stateText}>Loading wallets…</Text>}
      {query.isError && <Text style={styles.errorText}>{(query.error as Error).message}</Text>}
      {query.isSuccess && query.data.wallets.length === 0 && (
        <Text style={styles.stateText}>No wallets yet — add your first bank account, card, or cash wallet.</Text>
      )}

      <FlatList
        data={query.data?.wallets ?? []}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{gap: spacing.sm}}
        renderItem={({item}) => (
          <Pressable
            style={styles.card}
            onPress={() => navigation.navigate('WalletDetail', {walletId: item.id})}>
            <View style={{flex: 1}}>
              <Text style={styles.walletName}>{item.name}</Text>
              <Text style={styles.walletType}>{WALLET_TYPE_LABELS[item.type]}</Text>
            </View>
            <MoneyText
              amount={item.current_balance}
              negative={LIABILITY_TYPES.has(item.type) && item.current_balance > 0}
              positive={!LIABILITY_TYPES.has(item.type)}
            />
          </Pressable>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  header: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg},
  title: {color: colors.textPrimary, fontSize: 22, fontWeight: '600'},
  addButton: {backgroundColor: colors.accent, borderRadius: radius.pill, paddingVertical: spacing.xs, paddingHorizontal: spacing.md},
  addButtonText: {color: colors.textPrimary, fontWeight: '600'},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl},
  errorText: {color: colors.negative, textAlign: 'center', marginTop: spacing.xl},
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  walletName: {color: colors.textPrimary, fontSize: 16, fontWeight: '600'},
  walletType: {color: colors.textSecondary, fontSize: 13, marginTop: 2},
});

import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {walletsApi} from '@/api/client';
import {MoneyText} from '@/components/MoneyText';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'WalletReconcile'>;

export function WalletReconcileScreen({route, navigation}: Props) {
  const {walletId} = route.params;
  const queryClient = useQueryClient();
  const [actualBalance, setActualBalance] = useState('');
  const [confirming, setConfirming] = useState(false);

  const walletQuery = useQuery({queryKey: ['wallets', walletId], queryFn: () => walletsApi.get(walletId)});

  const mutation = useMutation({
    mutationFn: () => walletsApi.reconcile(walletId, Number(actualBalance)),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['wallets']});
      queryClient.invalidateQueries({queryKey: ['wallets', walletId]});
      queryClient.invalidateQueries({queryKey: ['wallets', walletId, 'balance-history']});
      navigation.goBack();
    },
  });

  const wallet = walletQuery.data;
  const delta = wallet && actualBalance.trim() !== '' ? Number(actualBalance) - wallet.current_balance : null;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Reconcile {wallet?.name ?? 'wallet'}</Text>
      <Text style={styles.help}>
        Enter the real balance from your bank/card statement. Ledger will record the difference as an
        adjustment — it never overwrites the balance silently.
      </Text>

      {wallet && (
        <View style={styles.currentRow}>
          <Text style={styles.currentLabel}>Current balance in Ledger</Text>
          <MoneyText amount={wallet.current_balance} />
        </View>
      )}

      <Text style={styles.label}>Actual balance</Text>
      <TextInput
        style={styles.input}
        value={actualBalance}
        onChangeText={(v) => {
          setActualBalance(v);
          setConfirming(false);
        }}
        keyboardType="numeric"
        placeholder="0.00"
        placeholderTextColor={colors.textSecondary}
      />

      {delta !== null && (
        <Text style={[styles.deltaText, {color: delta >= 0 ? colors.positive : colors.negative}]}>
          {delta >= 0 ? '+' : ''}
          {delta.toFixed(2)} adjustment will be recorded
        </Text>
      )}

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      {!confirming ? (
        <Pressable
          style={styles.button}
          disabled={actualBalance.trim() === ''}
          onPress={() => setConfirming(true)}>
          <Text style={styles.buttonText}>Review</Text>
        </Pressable>
      ) : (
        <>
          <Text style={styles.confirmText}>Confirm this adjustment?</Text>
          <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending}>
            <Text style={styles.buttonText}>{mutation.isPending ? 'Saving…' : 'Confirm reconcile'}</Text>
          </Pressable>
          <Pressable style={styles.cancelButton} onPress={() => setConfirming(false)}>
            <Text style={styles.cancelButtonText}>Back</Text>
          </Pressable>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  title: {color: colors.textPrimary, fontSize: 20, fontWeight: '600', marginBottom: spacing.sm},
  help: {color: colors.textSecondary, fontSize: 13, marginBottom: spacing.lg, lineHeight: 18},
  currentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  currentLabel: {color: colors.textSecondary, fontSize: 13},
  label: {color: colors.textSecondary, fontSize: 13, marginBottom: spacing.xs},
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    padding: spacing.md,
    marginBottom: spacing.sm,
    fontSize: 18,
  },
  deltaText: {fontSize: 14, marginBottom: spacing.md},
  confirmText: {color: colors.textPrimary, fontSize: 14, marginBottom: spacing.sm, textAlign: 'center'},
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center', marginTop: spacing.sm},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  cancelButton: {alignItems: 'center', padding: spacing.sm, marginTop: spacing.xs},
  cancelButtonText: {color: colors.textSecondary},
  error: {color: colors.negative, marginBottom: spacing.sm},
});

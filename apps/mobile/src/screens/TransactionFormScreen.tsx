import React, {useEffect, useState} from 'react';
import {Pressable, ScrollView, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {categoriesApi, transactionsApi, walletsApi} from '@/api/client';
import {PickerField} from '@/components/PickerField';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'TransactionForm'>;
type TxnType = 'expense' | 'income';

export function TransactionFormScreen({route, navigation}: Props) {
  const transactionId = route.params?.transactionId;
  const isEdit = !!transactionId;
  const queryClient = useQueryClient();

  const [type, setType] = useState<TxnType>('expense');
  const [walletId, setWalletId] = useState<string | null>(route.params?.walletId ?? null);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [amount, setAmount] = useState('');
  const [merchantName, setMerchantName] = useState('');
  const [note, setNote] = useState('');

  const walletsQuery = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});
  const categoriesQuery = useQuery({
    queryKey: ['categories', type],
    queryFn: () => categoriesApi.list({type}),
  });
  const existingQuery = useQuery({
    queryKey: ['transactions', transactionId],
    queryFn: () => transactionsApi.get(transactionId as string),
    enabled: isEdit,
  });

  useEffect(() => {
    if (existingQuery.data) {
      const txn = existingQuery.data;
      setType(txn.type === 'income' ? 'income' : 'expense');
      setWalletId(txn.wallet_id);
      setCategoryId(txn.category_id);
      setAmount(String(txn.amount));
      setMerchantName(txn.merchant_name ?? '');
      setNote(txn.note ?? '');
    }
  }, [existingQuery.data]);

  const createMutation = useMutation({
    mutationFn: () =>
      transactionsApi.create({
        wallet_id: walletId as string,
        category_id: categoryId as string,
        type,
        amount: Number(amount),
        merchant_name: merchantName || undefined,
        note: note || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['transactions']});
      queryClient.invalidateQueries({queryKey: ['wallets']});
      navigation.goBack();
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      transactionsApi.update(transactionId as string, {
        wallet_id: walletId ?? undefined,
        category_id: categoryId ?? undefined,
        amount: Number(amount),
        merchant_name: merchantName || undefined,
        note: note || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['transactions']});
      queryClient.invalidateQueries({queryKey: ['wallets']});
      navigation.goBack();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => transactionsApi.remove(transactionId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['transactions']});
      queryClient.invalidateQueries({queryKey: ['wallets']});
      navigation.goBack();
    },
  });

  const mutation = isEdit ? updateMutation : createMutation;
  const canSubmit = walletId && categoryId && Number(amount) > 0;

  const walletOptions = (walletsQuery.data?.wallets ?? []).map((w) => ({
    label: w.name,
    value: w.id,
    sublabel: w.type.replace('_', ' '),
  }));
  const categoryOptions = (categoriesQuery.data?.categories ?? [])
    .filter((c) => c.name !== 'Balance Adjustment')
    .map((c) => ({label: c.name, value: c.id}));

  return (
    <ScrollView style={styles.container} contentContainerStyle={{paddingBottom: spacing.xl}}>
      <Text style={styles.title}>{isEdit ? 'Edit transaction' : 'Add transaction'}</Text>

      {!isEdit && (
        <View style={styles.typeRow}>
          {(['expense', 'income'] as TxnType[]).map((t) => (
            <Pressable
              key={t}
              style={[styles.typeChip, type === t && styles.typeChipSelected]}
              onPress={() => {
                setType(t);
                setCategoryId(null);
              }}>
              <Text style={type === t ? styles.typeChipTextSelected : styles.typeChipText}>
                {t === 'expense' ? 'Expense' : 'Income'}
              </Text>
            </Pressable>
          ))}
        </View>
      )}

      <Text style={styles.label}>Amount</Text>
      <TextInput
        style={styles.amountInput}
        value={amount}
        onChangeText={setAmount}
        keyboardType="numeric"
        placeholder="0.00"
        placeholderTextColor={colors.textSecondary}
      />

      <PickerField label="Wallet" options={walletOptions} value={walletId} onChange={setWalletId} />
      <PickerField label="Category" options={categoryOptions} value={categoryId} onChange={setCategoryId} />

      <Text style={styles.label}>Merchant (optional)</Text>
      <TextInput style={styles.input} value={merchantName} onChangeText={setMerchantName} placeholderTextColor={colors.textSecondary} placeholder="e.g. Swiggy" />

      <Text style={styles.label}>Note (optional)</Text>
      <TextInput style={styles.input} value={note} onChangeText={setNote} placeholderTextColor={colors.textSecondary} placeholder="Add a note" />

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={!canSubmit || mutation.isPending}>
        <Text style={styles.buttonText}>{mutation.isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Add transaction'}</Text>
      </Pressable>

      {isEdit && (
        <Pressable style={styles.deleteButton} onPress={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
          <Text style={styles.deleteButtonText}>{deleteMutation.isPending ? 'Deleting…' : 'Delete transaction'}</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  title: {color: colors.textPrimary, fontSize: 22, fontWeight: '600', marginBottom: spacing.lg},
  typeRow: {flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.lg},
  typeChip: {
    flex: 1,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  typeChipSelected: {backgroundColor: colors.accent, borderColor: colors.accent},
  typeChipText: {color: colors.textSecondary, fontSize: 14},
  typeChipTextSelected: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  label: {color: colors.textSecondary, fontSize: 13, marginBottom: spacing.xs},
  amountInput: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    padding: spacing.md,
    marginBottom: spacing.md,
    fontSize: 28,
    fontVariant: ['tabular-nums'],
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center', marginTop: spacing.sm},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  deleteButton: {alignItems: 'center', padding: spacing.md, marginTop: spacing.sm},
  deleteButtonText: {color: colors.negative, fontSize: 14},
  error: {color: colors.negative, marginBottom: spacing.sm},
});

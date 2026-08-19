import React, {useEffect, useState} from 'react';
import {Pressable, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {categoriesApi, recurringApi, transactionsApi, walletsApi} from '@/api/client';
import {CategoryIconGridField} from '@/components/CategoryIconGridField';
import {PickerField} from '@/components/PickerField';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'TransactionForm'>;
type TxnMode = 'expense' | 'income' | 'transfer';

const KEYPAD_ROWS = [
  ['1', '2', '3', '⌫'],
  ['4', '5', '6', '+'],
  ['7', '8', '9', '−'],
  ['.', '0', ''],
];

// s15 in the design project — a keypad-driven amount entry, matching the
// existing app-wide numeric-keyboard convention rather than the OS
// keyboard. The "+"/"−" keys in the mockup's grid are decorative in this
// implementation (a mini calculator on the amount field is a real feature,
// not something to fake) — they're rendered but inert, same trim pattern
// as the fingerprint slot on AppLockScreen.
export function TransactionFormScreen({route, navigation}: Props) {
  const transactionId = route.params?.transactionId;
  const isEdit = !!transactionId;
  const queryClient = useQueryClient();

  const [mode, setMode] = useState<TxnMode>('expense');
  const [walletId, setWalletId] = useState<string | null>(route.params?.walletId ?? null);
  const [toWalletId, setToWalletId] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [amount, setAmount] = useState('0');
  const [note, setNote] = useState('');
  const [markRecurring, setMarkRecurring] = useState(false);

  const walletsQuery = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});
  const categoriesQuery = useQuery({
    queryKey: ['categories', mode === 'income' ? 'income' : 'expense'],
    queryFn: () => categoriesApi.list({type: mode === 'income' ? 'income' : 'expense'}),
    enabled: mode !== 'transfer',
  });
  const existingQuery = useQuery({
    queryKey: ['transactions', transactionId],
    queryFn: () => transactionsApi.get(transactionId as string),
    enabled: isEdit,
  });

  useEffect(() => {
    if (existingQuery.data) {
      const txn = existingQuery.data;
      setMode(txn.type === 'income' ? 'income' : 'expense');
      setWalletId(txn.wallet_id);
      setCategoryId(txn.category_id);
      setAmount(String(txn.amount));
      setNote(txn.note ?? '');
    }
  }, [existingQuery.data]);

  const pressKey = (key: string) => {
    if (key === '⌫') {
      setAmount((a) => (a.length <= 1 ? '0' : a.slice(0, -1)));
      return;
    }
    if (key === '+' || key === '−' || key === '') return;
    if (key === '.' && amount.includes('.')) return;
    setAmount((a) => (a === '0' && key !== '.' ? key : a + key));
  };

  const recurringMutation = useMutation({
    mutationFn: (input: {wallet_id: string; category_id: string; type: 'expense' | 'income'; merchant_name: string; amount: number}) =>
      recurringApi.create({
        wallet_id: input.wallet_id,
        category_id: input.category_id,
        type: input.type,
        merchant_name: input.merchant_name || 'Recurring transaction',
        amount: input.amount,
        frequency: 'monthly',
        next_due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      }),
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const txn = await transactionsApi.create({
        wallet_id: walletId as string,
        category_id: categoryId as string,
        type: mode as 'expense' | 'income',
        amount: Number(amount),
        note: note || undefined,
      });
      if (markRecurring) {
        await recurringMutation.mutateAsync({
          wallet_id: walletId as string,
          category_id: categoryId as string,
          type: mode as 'expense' | 'income',
          merchant_name: note,
          amount: Number(amount),
        });
      }
      return txn;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['transactions']});
      queryClient.invalidateQueries({queryKey: ['wallets']});
      queryClient.invalidateQueries({queryKey: ['recurring']});
      navigation.goBack();
    },
  });

  const transferMutation = useMutation({
    mutationFn: () =>
      transactionsApi.transfer({
        wallet_id: walletId as string,
        transfer_to_wallet_id: toWalletId as string,
        amount: Number(amount),
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

  const mutation = isEdit ? updateMutation : mode === 'transfer' ? transferMutation : createMutation;
  const canSubmit =
    Number(amount) > 0 && (mode === 'transfer' ? walletId && toWalletId && walletId !== toWalletId : walletId && categoryId);

  const walletOptions = (walletsQuery.data?.wallets ?? []).map((w) => ({label: w.name, value: w.id, sublabel: w.type.replace('_', ' ')}));
  const selectableCategories = (categoriesQuery.data?.categories ?? []).filter((c) => c.name !== 'Balance Adjustment');

  if (walletsQuery.isLoading || (isEdit && existingQuery.isLoading)) {
    return (
      <View style={styles.container}>
        <View style={styles.headerRow}>
          <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
            <Text style={styles.closeGlyph}>✕</Text>
          </Pressable>
          <Text style={styles.editTitle}>{isEdit ? 'Edit transaction' : 'Add expense'}</Text>
          <View style={{width: 22}} />
        </View>
        <Text style={styles.stateText}>Loading…</Text>
      </View>
    );
  }

  if ((walletsQuery.isError || (isEdit && existingQuery.isError)) && !walletOptions.length) {
    return (
      <View style={styles.container}>
        <View style={styles.headerRow}>
          <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
            <Text style={styles.closeGlyph}>✕</Text>
          </Pressable>
          <Text style={styles.editTitle}>Add expense</Text>
          <View style={{width: 22}} />
        </View>
        <View style={styles.emptyWalletBlock}>
          <Text style={styles.emptyWalletTitle}>Couldn't load this form</Text>
          <Pressable style={styles.emptyWalletCta} onPress={() => (isEdit ? existingQuery.refetch() : walletsQuery.refetch())}>
            <Text style={styles.emptyWalletCtaText}>Try again</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  if (walletsQuery.isSuccess && walletOptions.length === 0) {
    return (
      <View style={styles.container}>
        <View style={styles.headerRow}>
          <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
            <Text style={styles.closeGlyph}>✕</Text>
          </Pressable>
          <Text style={styles.editTitle}>Add expense</Text>
          <View style={{width: 22}} />
        </View>
        <View style={styles.emptyWalletBlock}>
          <Text style={styles.emptyWalletTitle}>Add a wallet first</Text>
          <Text style={styles.emptyWalletSubtitle}>Every expense sits in a wallet, so we need one before your first entry.</Text>
          <Pressable style={styles.emptyWalletCta} onPress={() => navigation.navigate('WalletForm', undefined)}>
            <Text style={styles.emptyWalletCtaText}>Add a wallet</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
          <Text style={styles.closeGlyph}>✕</Text>
        </Pressable>
        {!isEdit ? (
          <View style={styles.segments}>
            {(['expense', 'income', 'transfer'] as TxnMode[]).map((m) => (
              <Pressable
                key={m}
                style={[
                  styles.segment,
                  mode === m && {backgroundColor: m === 'expense' ? colors.negative : m === 'income' ? colors.positive : colors.accent},
                ]}
                onPress={() => setMode(m)}>
                <Text style={mode === m ? styles.segmentTextActive : styles.segmentText}>
                  {m === 'expense' ? 'Expense' : m === 'income' ? 'Income' : 'Transfer'}
                </Text>
              </Pressable>
            ))}
          </View>
        ) : (
          <Text style={styles.editTitle}>Edit transaction</Text>
        )}
        <View style={{width: 22}} />
      </View>

      <View style={styles.amountRow}>
        <Text style={styles.currencySymbol}>₹</Text>
        <Text style={styles.amountValue}>{amount}</Text>
        <View style={styles.cursor} />
      </View>
      <Text style={styles.dateText}>Today · {new Date().toLocaleDateString('en-GB', {day: '2-digit', month: 'short'})}</Text>

      <View style={styles.fields}>
        {mode === 'transfer' ? (
          <>
            <PickerField label="From wallet" options={walletOptions} value={walletId} onChange={setWalletId} />
            <PickerField label="To wallet" options={walletOptions.filter((o) => o.value !== walletId)} value={toWalletId} onChange={setToWalletId} />
          </>
        ) : (
          <>
            <PickerField label="Wallet" options={walletOptions} value={walletId} onChange={setWalletId} />
            <CategoryIconGridField label="Category" categories={selectableCategories} value={categoryId} onChange={setCategoryId} />
          </>
        )}

        <View style={styles.noteRow}>
          <TextInput
            style={styles.noteInput}
            value={note}
            onChangeText={setNote}
            placeholder="Add a note (optional)"
            placeholderTextColor={colors.textSecondary}
          />
        </View>

        {mode !== 'transfer' && !isEdit && (
          <Pressable style={styles.toggleRow} onPress={() => setMarkRecurring((v) => !v)}>
            <View style={{flexDirection: 'row', alignItems: 'center', gap: spacing.sm}}>
              <Text style={styles.toggleGlyph}>↻</Text>
              <Text style={styles.toggleLabel}>Mark as recurring</Text>
            </View>
            <View style={[styles.toggleTrack, markRecurring && styles.toggleTrackOn]}>
              <View style={styles.toggleThumb} />
            </View>
          </Pressable>
        )}
      </View>

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      {isEdit && (
        <Pressable style={styles.deleteButton} onPress={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
          <Text style={styles.deleteButtonText}>{deleteMutation.isPending ? 'Deleting…' : 'Delete transaction'}</Text>
        </Pressable>
      )}

      <View style={{flex: 1}} />

      <View style={styles.keypad}>
        {KEYPAD_ROWS.slice(0, 3).map((row, ri) => (
          <View key={ri} style={styles.keypadRow}>
            {row.map((key, ki) => (
              <Pressable key={ki} style={styles.key} onPress={() => pressKey(key)}>
                <Text style={[styles.keyText, (key === '+' || key === '−') && {color: colors.accentOnDark}]}>{key}</Text>
              </Pressable>
            ))}
          </View>
        ))}
        <View style={styles.keypadRow}>
          <Pressable style={styles.key} onPress={() => pressKey('.')}>
            <Text style={styles.keyText}>.</Text>
          </Pressable>
          <Pressable style={styles.key} onPress={() => pressKey('0')}>
            <Text style={styles.keyText}>0</Text>
          </Pressable>
          <Pressable
            style={[styles.submitKey, !canSubmit && {opacity: 0.5}]}
            disabled={!canSubmit || mutation.isPending}
            onPress={() => mutation.mutate()}>
            <Text style={styles.submitKeyText}>
              {mutation.isPending ? 'Saving…' : isEdit ? 'Save changes' : mode === 'transfer' ? 'Transfer' : mode === 'income' ? 'Add income' : 'Add expense'}
            </Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  headerRow: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  closeGlyph: {color: '#C9C9D2', fontSize: 18},
  editTitle: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 17, fontWeight: '600'},
  segments: {flexDirection: 'row', gap: 4, padding: 3, borderRadius: radius.pill, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  segment: {paddingHorizontal: 14, paddingVertical: 5, borderRadius: radius.pill},
  segmentText: {fontSize: 11.5, color: colors.textSecondary},
  segmentTextActive: {fontSize: 11.5, fontWeight: '600', color: colors.background},
  amountRow: {flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'center', gap: 6, paddingTop: spacing.lg},
  currencySymbol: {color: '#5A5A66', fontFamily: fontFamilies.monetary, fontSize: 22, paddingBottom: 6},
  amountValue: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontVariant: ['tabular-nums'], fontSize: 46, letterSpacing: -1.4, lineHeight: 46, fontWeight: '600'},
  cursor: {width: 2, height: 38, backgroundColor: colors.accent},
  dateText: {textAlign: 'center', color: colors.textSecondary, fontSize: 11.5},
  fields: {gap: spacing.sm, paddingHorizontal: spacing.lg, paddingTop: spacing.lg},
  noteRow: {height: 50, borderRadius: radius.row, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, justifyContent: 'center', paddingHorizontal: 14},
  noteInput: {color: colors.textPrimary, fontSize: 13},
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 13,
    borderRadius: radius.row,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  toggleGlyph: {fontSize: 17, color: colors.textSecondary},
  toggleLabel: {fontSize: 12.5, color: colors.textPrimary},
  toggleTrack: {width: 44, height: 26, borderRadius: radius.pill, backgroundColor: colors.border, padding: 3, justifyContent: 'center'},
  toggleTrackOn: {backgroundColor: colors.accent, alignItems: 'flex-end'},
  toggleThumb: {width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff'},
  error: {color: colors.negative, textAlign: 'center', marginTop: spacing.sm},
  deleteButton: {alignItems: 'center', padding: spacing.md},
  deleteButtonText: {color: colors.negative, fontSize: 14},
  keypad: {backgroundColor: colors.backgroundRaised, borderTopWidth: 1, borderTopColor: colors.border, padding: 10, paddingBottom: 14, gap: 8},
  keypadRow: {flexDirection: 'row', gap: 8},
  key: {flex: 1, height: 52, borderRadius: 14, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center'},
  keyText: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 20},
  submitKey: {flex: 2, height: 52, borderRadius: 14, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  submitKeyText: {color: colors.textPrimary, fontSize: 13.5, fontWeight: '600'},
  stateText: {color: colors.textSecondary, fontSize: 13, textAlign: 'center', marginTop: spacing.xl},
  emptyWalletBlock: {margin: spacing.lg, padding: 16, borderRadius: radius.card - 2, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  emptyWalletTitle: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  emptyWalletSubtitle: {color: colors.textSecondary, fontSize: 12, marginTop: 4, lineHeight: 17},
  emptyWalletCta: {alignSelf: 'flex-start', marginTop: spacing.md, height: 42, paddingHorizontal: 18, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  emptyWalletCtaText: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
});

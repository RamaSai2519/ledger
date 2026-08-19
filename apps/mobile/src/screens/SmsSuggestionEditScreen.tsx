import React, {useState} from 'react';
import {Pressable, ScrollView, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import type {RootStackParamList} from '@/navigation/types';
import {categoriesApi, smsApi, walletsApi} from '@/api/client';
import {PickerField} from '@/components/PickerField';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'SmsSuggestionEdit'>;

// "Edit before saving" step (s23 in the design project) reached from the
// inline SMS suggestion card's pencil button — lets the household correct the
// wallet/category/amount the backend guessed before it becomes a real
// transaction. There's no "original message" preview here (unlike the
// mockup) because raw_text is intentionally never sent to the client
// (data-minimization, plan.md §2.3) — only the already-extracted fields
// below ever reach this screen.
export function SmsSuggestionEditScreen({route, navigation}: Props) {
  const {suggestion} = route.params;
  const queryClient = useQueryClient();
  const txnType = suggestion.parsed_direction === 'credit' ? 'income' : 'expense';

  const [amount, setAmount] = useState(String(suggestion.parsed_amount ?? ''));
  const [walletId, setWalletId] = useState<string | null>(suggestion.suggested_wallet_id);
  const [categoryId, setCategoryId] = useState<string | null>(suggestion.suggested_category_id);
  const [justAdded, setJustAdded] = useState(false);

  const walletsQuery = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});
  const categoriesQuery = useQuery({
    queryKey: ['categories', txnType],
    queryFn: () => categoriesApi.list({type: txnType}),
  });

  const acceptMutation = useMutation({
    mutationFn: () =>
      smsApi.accept(suggestion.id, {
        wallet_id: walletId as string,
        category_id: categoryId as string,
        amount: Number(amount),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['sms', 'suggestions']});
      queryClient.invalidateQueries({queryKey: ['transactions']});
      queryClient.invalidateQueries({queryKey: ['wallets']});
      setJustAdded(true);
      setTimeout(() => navigation.navigate('Home'), 700);
    },
  });

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
    <ScrollView style={styles.container} contentContainerStyle={{padding: spacing.lg, paddingBottom: spacing.xl}}>
      <View style={styles.sourceCard}>
        <Text style={styles.sourceLabel}>Detected · {suggestion.sender_id}</Text>
        <Text style={styles.sourceMerchant}>{suggestion.parsed_merchant ?? 'Unknown merchant'}</Text>
      </View>

      <View style={styles.amountRow}>
        <Text style={styles.currencySymbol}>₹</Text>
        <TextInput
          style={styles.amountInput}
          value={amount}
          onChangeText={setAmount}
          keyboardType="numeric"
          placeholder="0"
          placeholderTextColor={colors.textSecondary}
        />
      </View>

      <PickerField label="Wallet" options={walletOptions} value={walletId} onChange={setWalletId} />
      <PickerField label="Category" options={categoryOptions} value={categoryId} onChange={setCategoryId} />

      <Text style={styles.hint}>We'll remember this pairing for future Swiggy-style suggestions.</Text>

      {acceptMutation.isError && <Text style={styles.error}>{(acceptMutation.error as Error).message}</Text>}

      {justAdded ? (
        <View style={styles.toast}>
          <MaterialIcons name="check-circle" style={styles.toastIcon} />
          <Text style={styles.toastText}>Added</Text>
        </View>
      ) : (
        <Pressable style={styles.button} onPress={() => acceptMutation.mutate()} disabled={!canSubmit || acceptMutation.isPending}>
          <Text style={styles.buttonText}>{acceptMutation.isPending ? 'Adding…' : txnType === 'income' ? 'Add income' : 'Add expense'}</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  sourceCard: {
    padding: 12,
    borderRadius: radius.row,
    backgroundColor: colors.backgroundRaised,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.md,
  },
  sourceLabel: {color: colors.textSecondary, fontSize: 10.5, textTransform: 'uppercase', letterSpacing: 0.5},
  sourceMerchant: {color: colors.textPrimary, fontSize: 13, fontWeight: '600', marginTop: 4},
  amountRow: {flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'center', gap: spacing.xs, paddingVertical: spacing.md},
  currencySymbol: {color: colors.textSecondary, fontFamily: fontFamilies.monetary, fontSize: 20, paddingBottom: 8},
  amountInput: {
    color: colors.textPrimary,
    fontFamily: fontFamilies.display,
    fontSize: 42,
    letterSpacing: -1.3,
    minWidth: 80,
    textAlign: 'center',
    padding: 0,
  },
  hint: {color: colors.textSecondary, fontSize: 11.5, marginTop: spacing.xs, marginBottom: spacing.md},
  error: {color: colors.negative, marginBottom: spacing.sm},
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center', marginTop: spacing.sm},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: radius.pill,
    padding: spacing.md,
    marginTop: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: 'rgba(47,217,136,.35)',
  },
  toastIcon: {color: colors.positive, fontSize: 18},
  toastText: {color: colors.textPrimary, fontWeight: '600'},
});

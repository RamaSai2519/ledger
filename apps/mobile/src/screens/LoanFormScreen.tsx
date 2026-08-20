import React, {useEffect, useState} from 'react';
import {Pressable, ScrollView, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import {categoriesApi, loansApi, walletsApi} from '@/api/client';
import {CategoryIconGridField} from '@/components/CategoryIconGridField';
import {PickerField} from '@/components/PickerField';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'LoanForm'>;

export function LoanFormScreen({route, navigation}: Props) {
  const loanId = route.params?.loanId;
  const isEdit = !!loanId;
  const queryClient = useQueryClient();

  // No GET /loans/<id> on the backend (mirrors recurring_rules) — fetch via
  // list() and find, same as RecurringRuleFormScreen does for its rule.
  const existingQuery = useQuery({
    queryKey: ['loans', loanId],
    queryFn: async () => (await loansApi.list()).loans.find((l) => l.id === loanId),
    enabled: isEdit,
  });

  const [name, setName] = useState('');
  const [walletId, setWalletId] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [principal, setPrincipal] = useState('');
  const [annualInterestRate, setAnnualInterestRate] = useState('');
  const [tenureMonths, setTenureMonths] = useState('');
  const [emiAmount, setEmiAmount] = useState('');
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [isActive, setIsActive] = useState(true);

  const walletsQuery = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});
  const categoriesQuery = useQuery({queryKey: ['categories', 'expense'], queryFn: () => categoriesApi.list({type: 'expense'})});

  const loaded = existingQuery.data;
  useEffect(() => {
    if (loaded) {
      setName(loaded.name);
      setWalletId(loaded.wallet_id);
      setCategoryId(loaded.category_id);
      setPrincipal(String(loaded.principal));
      setAnnualInterestRate(String(loaded.annual_interest_rate));
      setTenureMonths(String(loaded.tenure_months));
      setEmiAmount(String(loaded.emi_amount));
      setStartDate(loaded.start_date.slice(0, 10));
      setIsActive(loaded.is_active);
    }
  }, [loaded]);

  const createMutation = useMutation({
    mutationFn: () =>
      loansApi.create({
        name: name.trim(),
        wallet_id: walletId as string,
        category_id: categoryId as string,
        principal: Number(principal),
        annual_interest_rate: Number(annualInterestRate),
        tenure_months: Number(tenureMonths),
        emi_amount: Number(emiAmount),
        start_date: startDate,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['loans']});
      navigation.goBack();
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      loansApi.update(loanId as string, {
        name: name.trim(),
        wallet_id: walletId ?? undefined,
        category_id: categoryId ?? undefined,
        emi_amount: Number(emiAmount),
        is_active: isActive,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['loans']});
      navigation.goBack();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => loansApi.remove(loanId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['loans']});
      navigation.goBack();
    },
  });

  const mutation = isEdit ? updateMutation : createMutation;
  const canSubmit = isEdit
    ? name.trim() && walletId && categoryId && Number(emiAmount) > 0
    : name.trim() &&
      walletId &&
      categoryId &&
      Number(principal) > 0 &&
      Number(annualInterestRate) >= 0 &&
      Number(tenureMonths) > 0 &&
      Number(emiAmount) > 0 &&
      startDate;

  const walletOptions = (walletsQuery.data?.wallets ?? []).map((w) => ({label: w.name, value: w.id}));
  const selectableCategories = (categoriesQuery.data?.categories ?? []).filter((c) => c.name !== 'Balance Adjustment');

  return (
    <ScrollView style={styles.container} contentContainerStyle={{padding: spacing.lg, paddingBottom: spacing.xl}}>
      <Text style={styles.title}>{isEdit ? 'Edit loan' : 'New loan'}</Text>

      <Text style={styles.label}>Name</Text>
      <TextInput style={styles.input} value={name} onChangeText={setName} placeholder="e.g. Bike Loan" placeholderTextColor={colors.textSecondary} />

      <PickerField label="EMI source wallet" options={walletOptions} value={walletId} onChange={setWalletId} />
      <CategoryIconGridField label="Category" categories={selectableCategories} value={categoryId} onChange={setCategoryId} />

      {/* Principal, interest rate, tenure and start date are immutable once
          a loan is created (backend's loan_update PATCHABLE_FIELDS excludes
          them) — hidden in edit mode rather than shown disabled, since
          they're not relevant to editing at that point. */}
      {!isEdit && (
        <>
          <Text style={styles.label}>Principal</Text>
          <TextInput style={styles.input} value={principal} onChangeText={setPrincipal} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />

          <Text style={styles.label}>Annual interest rate (%)</Text>
          <TextInput
            style={styles.input}
            value={annualInterestRate}
            onChangeText={setAnnualInterestRate}
            keyboardType="numeric"
            placeholderTextColor={colors.textSecondary}
          />

          <Text style={styles.label}>Tenure (months)</Text>
          <TextInput style={styles.input} value={tenureMonths} onChangeText={setTenureMonths} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />

          <Text style={styles.label}>Start date</Text>
          <TextInput style={styles.input} value={startDate} onChangeText={setStartDate} placeholder="YYYY-MM-DD" placeholderTextColor={colors.textSecondary} />
        </>
      )}

      <Text style={styles.label}>EMI amount</Text>
      <TextInput style={styles.input} value={emiAmount} onChangeText={setEmiAmount} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />

      {isEdit && (
        <Pressable style={styles.toggleRow} onPress={() => setIsActive((v) => !v)}>
          <Text style={styles.toggleLabel}>Active</Text>
          <View style={[styles.toggleTrack, isActive && styles.toggleTrackOn]}>
            <View style={styles.toggleThumb} />
          </View>
        </Pressable>
      )}

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={!canSubmit || mutation.isPending}>
        <Text style={styles.buttonText}>{mutation.isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Create loan'}</Text>
      </Pressable>

      {isEdit && (
        <Pressable style={styles.deleteButton} onPress={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
          <Text style={styles.deleteButtonText}>{deleteMutation.isPending ? 'Deleting…' : 'Delete loan'}</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  title: {color: colors.textPrimary, fontSize: 20, fontWeight: '600', marginBottom: spacing.lg},
  label: {color: colors.textSecondary, fontSize: 13, marginBottom: spacing.xs, marginTop: spacing.sm},
  input: {backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, color: colors.textPrimary, padding: spacing.md, marginBottom: spacing.sm},
  toggleRow: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.md, marginTop: spacing.sm, marginBottom: spacing.sm},
  toggleLabel: {color: colors.textPrimary, fontSize: 13},
  toggleTrack: {width: 44, height: 26, borderRadius: radius.pill, backgroundColor: colors.border, padding: 3, justifyContent: 'center'},
  toggleTrackOn: {backgroundColor: colors.accent, alignItems: 'flex-end'},
  toggleThumb: {width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff'},
  error: {color: colors.negative, marginTop: spacing.sm},
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center', marginTop: spacing.lg},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  deleteButton: {alignItems: 'center', padding: spacing.md, marginTop: spacing.sm},
  deleteButtonText: {color: colors.negative, fontWeight: '600'},
});

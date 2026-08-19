import React, {useEffect, useState} from 'react';
import {Pressable, ScrollView, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {RecurringFrequency} from '@/api/client';
import {categoriesApi, recurringApi, walletsApi} from '@/api/client';
import {CategoryIconGridField} from '@/components/CategoryIconGridField';
import {PickerField} from '@/components/PickerField';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'RecurringRuleForm'>;

const FREQUENCIES: {value: RecurringFrequency; label: string}[] = [
  {value: 'weekly', label: 'Weekly'},
  {value: 'monthly', label: 'Monthly'},
  {value: 'yearly', label: 'Yearly'},
];

export function RecurringRuleFormScreen({route, navigation}: Props) {
  const ruleId = route.params?.ruleId;
  const isEdit = !!ruleId;
  const queryClient = useQueryClient();

  const existingQuery = useQuery({
    queryKey: ['recurring', ruleId],
    queryFn: async () => (await recurringApi.list()).recurring_rules.find((r) => r.id === ruleId),
    enabled: isEdit,
  });

  const [type, setType] = useState<'expense' | 'income'>('expense');
  const [walletId, setWalletId] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [merchantName, setMerchantName] = useState('');
  const [amount, setAmount] = useState('');
  const [varies, setVaries] = useState(false);
  const [frequency, setFrequency] = useState<RecurringFrequency>('monthly');
  const [nextDueDate, setNextDueDate] = useState(new Date().toISOString().slice(0, 10));
  const [autoCreate, setAutoCreate] = useState(false);
  const [isActive, setIsActive] = useState(true);

  const walletsQuery = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});
  const categoriesQuery = useQuery({queryKey: ['categories', type], queryFn: () => categoriesApi.list({type})});

  const loaded = existingQuery.data;
  useEffect(() => {
    if (loaded) {
      setType(loaded.type);
      setWalletId(loaded.wallet_id);
      setCategoryId(loaded.category_id);
      setMerchantName(loaded.merchant_name);
      setAmount(loaded.amount != null ? String(loaded.amount) : '');
      setVaries(loaded.amount == null);
      setFrequency(loaded.frequency);
      setNextDueDate(loaded.next_due_date.slice(0, 10));
      setAutoCreate(loaded.auto_create);
      setIsActive(loaded.is_active);
    }
  }, [loaded]);

  const createMutation = useMutation({
    mutationFn: () =>
      recurringApi.create({
        wallet_id: walletId as string,
        category_id: categoryId as string,
        type,
        merchant_name: merchantName.trim(),
        frequency,
        next_due_date: nextDueDate,
        amount: varies ? undefined : Number(amount),
        auto_create: autoCreate,
        is_active: isActive,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['recurring']});
      navigation.goBack();
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      recurringApi.update(ruleId as string, {
        wallet_id: walletId ?? undefined,
        category_id: categoryId ?? undefined,
        merchant_name: merchantName.trim(),
        frequency,
        next_due_date: nextDueDate,
        amount: varies ? undefined : Number(amount),
        auto_create: autoCreate,
        is_active: isActive,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['recurring']});
      navigation.goBack();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => recurringApi.remove(ruleId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['recurring']});
      navigation.goBack();
    },
  });

  const mutation = isEdit ? updateMutation : createMutation;
  const canSubmit = merchantName.trim() && walletId && categoryId && (varies || Number(amount) > 0);

  const walletOptions = (walletsQuery.data?.wallets ?? []).map((w) => ({label: w.name, value: w.id}));
  const selectableCategories = (categoriesQuery.data?.categories ?? []).filter((c) => c.name !== 'Balance Adjustment');

  return (
    <ScrollView style={styles.container} contentContainerStyle={{padding: spacing.lg, paddingBottom: spacing.xl}}>
      <Text style={styles.title}>{isEdit ? 'Edit recurring rule' : 'New recurring rule'}</Text>

      <View style={styles.typeRow}>
        {(['expense', 'income'] as const).map((t) => (
          <Pressable key={t} style={[styles.typeChip, type === t && styles.typeChipSelected]} onPress={() => setType(t)}>
            <Text style={type === t ? styles.typeChipTextSelected : styles.typeChipText}>{t === 'expense' ? 'Expense' : 'Income'}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>Merchant / label</Text>
      <TextInput style={styles.input} value={merchantName} onChangeText={setMerchantName} placeholder="e.g. Rent, Netflix" placeholderTextColor={colors.textSecondary} />

      <PickerField label="Wallet" options={walletOptions} value={walletId} onChange={setWalletId} />
      <CategoryIconGridField label="Category" categories={selectableCategories} value={categoryId} onChange={setCategoryId} />

      <Pressable style={styles.toggleRow} onPress={() => setVaries((v) => !v)}>
        <Text style={styles.toggleLabel}>Amount varies each cycle</Text>
        <View style={[styles.toggleTrack, varies && styles.toggleTrackOn]}>
          <View style={styles.toggleThumb} />
        </View>
      </Pressable>
      {!varies && (
        <>
          <Text style={styles.label}>Amount</Text>
          <TextInput style={styles.input} value={amount} onChangeText={setAmount} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
        </>
      )}

      <Text style={styles.label}>Frequency</Text>
      <View style={styles.typeRow}>
        {FREQUENCIES.map((f) => (
          <Pressable key={f.value} style={[styles.typeChip, frequency === f.value && styles.typeChipSelected]} onPress={() => setFrequency(f.value)}>
            <Text style={frequency === f.value ? styles.typeChipTextSelected : styles.typeChipText}>{f.label}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>Next due date</Text>
      <TextInput style={styles.input} value={nextDueDate} onChangeText={setNextDueDate} placeholder="YYYY-MM-DD" placeholderTextColor={colors.textSecondary} />

      <Pressable style={styles.toggleRow} onPress={() => setAutoCreate((v) => !v)}>
        <View style={{flex: 1}}>
          <Text style={styles.toggleLabel}>Add automatically</Text>
          <Text style={styles.toggleSubtitle}>Off sends a reminder to confirm instead.</Text>
        </View>
        <View style={[styles.toggleTrack, autoCreate && styles.toggleTrackOn]}>
          <View style={styles.toggleThumb} />
        </View>
      </Pressable>

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
        <Text style={styles.buttonText}>{mutation.isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Create rule'}</Text>
      </Pressable>

      {isEdit && (
        <Pressable style={styles.deleteButton} onPress={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
          <Text style={styles.deleteButtonText}>{deleteMutation.isPending ? 'Deleting…' : 'Delete rule'}</Text>
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
  typeRow: {flexDirection: 'row', gap: spacing.xs, marginBottom: spacing.sm},
  typeChip: {flex: 1, alignItems: 'center', borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, paddingVertical: spacing.sm},
  typeChipSelected: {backgroundColor: colors.accent, borderColor: colors.accent},
  typeChipText: {color: colors.textSecondary, fontSize: 13},
  typeChipTextSelected: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  toggleRow: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.md, marginTop: spacing.sm, marginBottom: spacing.sm},
  toggleLabel: {color: colors.textPrimary, fontSize: 13},
  toggleSubtitle: {color: colors.textSecondary, fontSize: 11, marginTop: 2},
  toggleTrack: {width: 44, height: 26, borderRadius: radius.pill, backgroundColor: colors.border, padding: 3, justifyContent: 'center'},
  toggleTrackOn: {backgroundColor: colors.accent, alignItems: 'flex-end'},
  toggleThumb: {width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff'},
  error: {color: colors.negative, marginTop: spacing.sm},
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center', marginTop: spacing.lg},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  deleteButton: {alignItems: 'center', padding: spacing.md, marginTop: spacing.sm},
  deleteButtonText: {color: colors.negative, fontWeight: '600'},
});

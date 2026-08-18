import React, {useState} from 'react';
import {Pressable, ScrollView, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {BudgetScope} from '@/api/client';
import {budgetsApi, categoriesApi, walletsApi} from '@/api/client';
import {PickerField} from '@/components/PickerField';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'BudgetForm'>;

const SCOPES: {value: BudgetScope; label: string}[] = [
  {value: 'overall', label: 'Overall'},
  {value: 'category', label: 'Category'},
  {value: 'wallet', label: 'Wallet'},
];

// A "two-number stepper" rather than a real slider component — no
// slider/range-input library is in the dependency tree yet, and the
// threshold_percents field is just a short sorted list of percents, so a
// pair of +/- steppers covers the MVP need (default 80/100) without adding
// a new native dependency for a two-value input.
function ThresholdStepper({label, value, onChange}: {label: string; value: number; onChange: (v: number) => void}) {
  const clamp = (v: number) => Math.min(200, Math.max(1, v));
  return (
    <View style={styles.stepperRow}>
      <Text style={styles.stepperLabel}>{label}</Text>
      <View style={styles.stepperControls}>
        <Pressable style={styles.stepperButton} onPress={() => onChange(clamp(value - 5))}>
          <Text style={styles.stepperButtonText}>−</Text>
        </Pressable>
        <Text style={styles.stepperValue}>{value}%</Text>
        <Pressable style={styles.stepperButton} onPress={() => onChange(clamp(value + 5))}>
          <Text style={styles.stepperButtonText}>+</Text>
        </Pressable>
      </View>
    </View>
  );
}

export function BudgetFormScreen({route, navigation}: Props) {
  const budgetId = route.params?.budgetId;
  const isEdit = !!budgetId;
  const queryClient = useQueryClient();

  const existingQuery = useQuery({
    queryKey: ['budgets', budgetId],
    queryFn: async () => (await budgetsApi.list()).budgets.find((b) => b.id === budgetId),
    enabled: isEdit,
  });

  const categoriesQuery = useQuery({queryKey: ['categories', 'expense'], queryFn: () => categoriesApi.list({type: 'expense'})});
  const walletsQuery = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});

  const [scope, setScope] = useState<BudgetScope>('overall');
  const [scopeRefId, setScopeRefId] = useState<string | null>(null);
  const [amount, setAmount] = useState('');
  const [thresholdLow, setThresholdLow] = useState(80);
  const [thresholdHigh, setThresholdHigh] = useState(100);

  const loaded = existingQuery.data;
  React.useEffect(() => {
    if (loaded) {
      setScope(loaded.scope);
      setScopeRefId(loaded.scope_ref_id);
      setAmount(String(loaded.amount));
      setThresholdLow(loaded.threshold_percents[0] ?? 80);
      setThresholdHigh(loaded.threshold_percents[1] ?? 100);
    }
  }, [loaded]);

  const thresholds = [thresholdLow, thresholdHigh].filter((t, i, arr) => arr.indexOf(t) === i).sort((a, b) => a - b);

  const createMutation = useMutation({
    mutationFn: () =>
      budgetsApi.create({
        scope,
        amount: Number(amount) || 0,
        scope_ref_id: scope === 'overall' ? undefined : scopeRefId ?? undefined,
        threshold_percents: thresholds,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['budgets']});
      navigation.goBack();
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      budgetsApi.update(budgetId as string, {amount: Number(amount) || 0, threshold_percents: thresholds}),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['budgets']});
      navigation.goBack();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => budgetsApi.remove(budgetId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['budgets']});
      navigation.goBack();
    },
  });

  const mutation = isEdit ? updateMutation : createMutation;
  const scopeRequiresRef = scope === 'category' || scope === 'wallet';
  const scopeOptions =
    scope === 'category'
      ? (categoriesQuery.data?.categories ?? []).map((c) => ({label: c.name, value: c.id}))
      : (walletsQuery.data?.wallets ?? []).map((w) => ({label: w.name, value: w.id}));

  const canSubmit = !!amount.trim() && (!scopeRequiresRef || !!scopeRefId);

  return (
    <ScrollView style={styles.container} contentContainerStyle={{paddingBottom: spacing.xl}}>
      <Text style={styles.title}>{isEdit ? 'Edit budget' : 'Add budget'}</Text>

      {!isEdit && (
        <>
          <Text style={styles.label}>Scope</Text>
          <View style={styles.scopeRow}>
            {SCOPES.map((s) => (
              <Pressable
                key={s.value}
                style={[styles.scopeChip, scope === s.value && styles.scopeChipSelected]}
                onPress={() => {
                  setScope(s.value);
                  setScopeRefId(null);
                }}>
                <Text style={scope === s.value ? styles.scopeChipTextSelected : styles.scopeChipText}>{s.label}</Text>
              </Pressable>
            ))}
          </View>

          {scopeRequiresRef && (
            <PickerField
              label={scope === 'category' ? 'Category' : 'Wallet'}
              options={scopeOptions}
              value={scopeRefId}
              onChange={setScopeRefId}
            />
          )}
        </>
      )}

      <Text style={styles.label}>Monthly cap</Text>
      <TextInput
        style={styles.input}
        value={amount}
        onChangeText={setAmount}
        keyboardType="numeric"
        placeholder="e.g. 15000"
        placeholderTextColor={colors.textSecondary}
      />

      <Text style={styles.label}>Alert thresholds</Text>
      <ThresholdStepper label="First alert" value={thresholdLow} onChange={setThresholdLow} />
      <ThresholdStepper label="Second alert" value={thresholdHigh} onChange={setThresholdHigh} />

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending || !canSubmit}>
        <Text style={styles.buttonText}>{mutation.isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Create budget'}</Text>
      </Pressable>

      {isEdit && (
        <Pressable style={styles.deleteButton} onPress={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
          <Text style={styles.deleteButtonText}>{deleteMutation.isPending ? 'Removing…' : 'Delete budget'}</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  title: {color: colors.textPrimary, fontSize: 22, fontWeight: '600', marginBottom: spacing.lg},
  label: {color: colors.textSecondary, fontSize: 13, marginBottom: spacing.xs, marginTop: spacing.sm},
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  scopeRow: {flexDirection: 'row', gap: spacing.xs, marginBottom: spacing.sm},
  scopeChip: {
    flex: 1,
    alignItems: 'center',
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.xs,
  },
  scopeChipSelected: {backgroundColor: colors.accent, borderColor: colors.accent},
  scopeChipText: {color: colors.textSecondary, fontSize: 13},
  scopeChipTextSelected: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  stepperRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.sm,
    marginBottom: spacing.sm,
  },
  stepperLabel: {color: colors.textPrimary, fontSize: 14},
  stepperControls: {flexDirection: 'row', alignItems: 'center', gap: spacing.sm},
  stepperButton: {
    width: 28,
    height: 28,
    borderRadius: radius.pill,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepperButtonText: {color: colors.textPrimary, fontSize: 16, fontWeight: '600'},
  stepperValue: {color: colors.textPrimary, fontSize: 14, fontWeight: '600', minWidth: 40, textAlign: 'center'},
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center', marginTop: spacing.lg},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  deleteButton: {alignItems: 'center', padding: spacing.md, marginTop: spacing.sm},
  deleteButtonText: {color: colors.negative, fontWeight: '600'},
  error: {color: colors.negative, marginTop: spacing.sm},
});

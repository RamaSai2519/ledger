import React, {useState} from 'react';
import {Pressable, ScrollView, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {BudgetScope} from '@/api/client';
import {budgetsApi, categoriesApi, walletsApi} from '@/api/client';
import {CategoryIconGridField} from '@/components/CategoryIconGridField';
import {PickerField} from '@/components/PickerField';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'BudgetForm'>;

const SCOPES: {value: BudgetScope; label: string}[] = [
  {value: 'category', label: 'Category'},
  {value: 'wallet', label: 'Wallet'},
  {value: 'overall', label: 'Overall'},
];

// A track+dot visual (matching s19 in the design project) driven by +/-
// steppers rather than a real drag gesture — no slider/range-input library
// is in the dependency tree, and threshold_percents is just a short sorted
// list of percents, so this covers the MVP need (default 80/100) without a
// new native dependency.
function ThresholdRow({label, value, onChange, color}: {label: string; value: number; onChange: (v: number) => void; color: string}) {
  const clamp = (v: number) => Math.min(200, Math.max(1, v));
  const trackPercent = Math.min(100, value);
  return (
    <View style={{marginTop: spacing.md}}>
      <View style={styles.thresholdHeader}>
        <Text style={styles.thresholdLabel}>{label}</Text>
        <Text style={[styles.thresholdValue, {color}]}>{value}%</Text>
      </View>
      <View style={styles.thresholdTrackWrap}>
        <View style={styles.thresholdTrack} />
        <View style={[styles.thresholdTrackFill, {width: `${trackPercent}%`, backgroundColor: color}]} />
        <View style={[styles.thresholdDot, {left: `${trackPercent}%`, borderColor: color}]} />
      </View>
      <View style={styles.stepperControls}>
        <Pressable style={styles.stepperButton} onPress={() => onChange(clamp(value - 5))}>
          <Text style={styles.stepperButtonText}>−</Text>
        </Pressable>
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

  const [scope, setScope] = useState<BudgetScope>('category');
  const [scopeRefId, setScopeRefId] = useState<string | null>(null);
  const [amount, setAmount] = useState('');
  const [thresholdLow, setThresholdLow] = useState(80);
  const [thresholdHigh, setThresholdHigh] = useState(100);
  const [notifyBoth, setNotifyBoth] = useState(true);

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
    mutationFn: () => budgetsApi.update(budgetId as string, {amount: Number(amount) || 0, threshold_percents: thresholds}),
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
    <ScrollView style={styles.container} contentContainerStyle={{padding: spacing.lg, paddingBottom: spacing.xl}}>
      <Text style={styles.title}>{isEdit ? 'Edit budget' : 'Add budget'}</Text>

      {!isEdit && (
        <>
          <Text style={styles.sectionLabel}>Applies to</Text>
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

          {scopeRequiresRef && scope === 'category' && (
            <CategoryIconGridField
              label="Category"
              categories={categoriesQuery.data?.categories ?? []}
              value={scopeRefId}
              onChange={setScopeRefId}
            />
          )}
          {scopeRequiresRef && scope === 'wallet' && (
            <PickerField label="Wallet" options={scopeOptions} value={scopeRefId} onChange={setScopeRefId} />
          )}
        </>
      )}

      <View style={styles.field}>
        <Text style={styles.fieldLabel}>Monthly limit</Text>
        <TextInput
          style={[styles.fieldInput, styles.fieldInputMono]}
          value={amount}
          onChangeText={setAmount}
          keyboardType="numeric"
          placeholder="e.g. 15000"
          placeholderTextColor={colors.textSecondary}
        />
      </View>

      <View style={styles.thresholdCard}>
        <ThresholdRow label="Warn me at" value={thresholdLow} onChange={setThresholdLow} color={colors.accentOnDark} />
        <ThresholdRow label="Alert again at" value={thresholdHigh} onChange={setThresholdHigh} color="#FF9B9B" />
        <Pressable style={styles.notifyRow} onPress={() => setNotifyBoth((v) => !v)}>
          <Text style={styles.notifyLabel}>Notify both of us</Text>
          <View style={[styles.toggleTrack, notifyBoth && styles.toggleTrackOn]}>
            <View style={styles.toggleThumb} />
          </View>
        </Pressable>
      </View>

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending || !canSubmit}>
        <Text style={styles.buttonText}>{mutation.isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Save budget'}</Text>
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
  container: {flex: 1, backgroundColor: colors.background},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 22, fontWeight: '600', marginBottom: spacing.lg},
  sectionLabel: {fontSize: 11, letterSpacing: 1, textTransform: 'uppercase', color: '#5A5A66', marginBottom: spacing.xs},
  scopeRow: {flexDirection: 'row', gap: spacing.xs, marginBottom: spacing.md},
  scopeChip: {flex: 1, alignItems: 'center', borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, paddingVertical: 11},
  scopeChipSelected: {backgroundColor: 'rgba(91,84,249,.12)', borderColor: colors.accent},
  scopeChipText: {color: colors.textSecondary, fontSize: 12},
  scopeChipTextSelected: {color: colors.textPrimary, fontSize: 12, fontWeight: '600'},
  field: {marginTop: spacing.md},
  fieldLabel: {fontSize: 11, letterSpacing: 0.5, textTransform: 'uppercase', color: colors.textSecondary, marginBottom: spacing.xs},
  fieldInput: {height: 60, borderRadius: radius.input, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, color: colors.textPrimary, paddingHorizontal: 14, fontSize: 20},
  fieldInputMono: {fontFamily: fontFamilies.monetary},
  thresholdCard: {marginTop: spacing.lg, padding: 16, borderRadius: radius.card - 2, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  thresholdHeader: {flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between'},
  thresholdLabel: {fontSize: 12.5, fontWeight: '600', color: colors.textPrimary},
  thresholdValue: {fontFamily: fontFamilies.monetary, fontSize: 13},
  thresholdTrackWrap: {height: 22, justifyContent: 'center', marginTop: spacing.xs},
  thresholdTrack: {position: 'absolute', left: 0, right: 0, height: 4, borderRadius: 2, backgroundColor: colors.border},
  thresholdTrackFill: {position: 'absolute', left: 0, height: 4, borderRadius: 2},
  thresholdDot: {position: 'absolute', width: 18, height: 18, borderRadius: 9, backgroundColor: colors.textPrimary, borderWidth: 3, marginLeft: -9},
  stepperControls: {flexDirection: 'row', gap: spacing.xs, marginTop: spacing.xs, alignSelf: 'flex-end'},
  stepperButton: {width: 26, height: 26, borderRadius: 13, backgroundColor: colors.backgroundRaised, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center'},
  stepperButtonText: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  notifyRow: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: spacing.lg},
  notifyLabel: {fontSize: 12.5, color: colors.textPrimary},
  toggleTrack: {width: 44, height: 26, borderRadius: radius.pill, backgroundColor: colors.border, padding: 3, justifyContent: 'center'},
  toggleTrackOn: {backgroundColor: colors.accent, alignItems: 'flex-end'},
  toggleThumb: {width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff'},
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center', marginTop: spacing.lg},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  deleteButton: {alignItems: 'center', padding: spacing.md, marginTop: spacing.sm},
  deleteButtonText: {color: colors.negative, fontWeight: '600'},
  error: {color: colors.negative, marginTop: spacing.sm},
});

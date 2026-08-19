import React, {useState} from 'react';
import {Pressable, ScrollView, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {WalletType} from '@/api/client';
import {walletsApi} from '@/api/client';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'WalletForm'>;

const WALLET_TYPES: {value: WalletType; label: string; glyph: string}[] = [
  {value: 'bank_account', label: 'Bank', glyph: 'B'},
  {value: 'credit_card', label: 'Credit card', glyph: 'C'},
  {value: 'pay_later', label: 'Pay later', glyph: 'P'},
  {value: 'cash', label: 'Cash', glyph: '₹'},
  {value: 'loan', label: 'Loan', glyph: 'L'},
];

function Field({label, children}: {label: string; children: React.ReactNode}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      {children}
    </View>
  );
}

export function WalletFormScreen({route, navigation}: Props) {
  const walletId = route.params?.walletId;
  const isEdit = !!walletId;
  const queryClient = useQueryClient();

  const existingQuery = useQuery({
    queryKey: ['wallets', walletId],
    queryFn: () => walletsApi.get(walletId as string),
    enabled: isEdit,
  });

  const [name, setName] = useState('');
  const [type, setType] = useState<WalletType>('bank_account');
  const [provider, setProvider] = useState('');
  const [accountLast4, setAccountLast4] = useState('');
  const [openingBalance, setOpeningBalance] = useState('0');

  const [creditLimit, setCreditLimit] = useState('');
  const [statementDay, setStatementDay] = useState('');
  const [dueDay, setDueDay] = useState('');
  const [minDuePercent, setMinDuePercent] = useState('');
  const [billingCycleDay, setBillingCycleDay] = useState('');
  const [principal, setPrincipal] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [tenureMonths, setTenureMonths] = useState('');
  const [emiAmount, setEmiAmount] = useState('');

  const loaded = existingQuery.data;
  React.useEffect(() => {
    if (loaded) {
      setName(loaded.name);
      setType(loaded.type);
      setProvider(loaded.provider ?? '');
      setAccountLast4(loaded.account_last4 ?? '');
      setOpeningBalance(String(loaded.opening_balance));
      if (loaded.credit_card_details) {
        setCreditLimit(String(loaded.credit_card_details.credit_limit ?? ''));
        setStatementDay(String(loaded.credit_card_details.statement_day ?? ''));
        setDueDay(String(loaded.credit_card_details.due_day ?? ''));
        setMinDuePercent(String(loaded.credit_card_details.min_due_percent ?? ''));
      }
      if (loaded.pay_later_details) {
        setCreditLimit(String(loaded.pay_later_details.credit_limit ?? ''));
        setBillingCycleDay(String(loaded.pay_later_details.billing_cycle_day ?? ''));
        setDueDay(String(loaded.pay_later_details.due_day ?? ''));
      }
      if (loaded.loan_details) {
        setPrincipal(String(loaded.loan_details.principal ?? ''));
        setInterestRate(String(loaded.loan_details.interest_rate ?? ''));
        setTenureMonths(String(loaded.loan_details.tenure_months ?? ''));
        setEmiAmount(String(loaded.loan_details.emi_amount ?? ''));
      }
    }
  }, [loaded]);

  const numOrUndefined = (v: string) => (v.trim() === '' ? undefined : Number(v));

  const buildTypeDetails = () => {
    if (type === 'credit_card') {
      return {
        credit_card_details: {
          credit_limit: numOrUndefined(creditLimit),
          statement_day: numOrUndefined(statementDay),
          due_day: numOrUndefined(dueDay),
          min_due_percent: numOrUndefined(minDuePercent),
        },
      };
    }
    if (type === 'pay_later') {
      return {
        pay_later_details: {
          credit_limit: numOrUndefined(creditLimit),
          billing_cycle_day: numOrUndefined(billingCycleDay),
          due_day: numOrUndefined(dueDay),
        },
      };
    }
    if (type === 'loan') {
      return {
        loan_details: {
          principal: numOrUndefined(principal),
          interest_rate: numOrUndefined(interestRate),
          tenure_months: numOrUndefined(tenureMonths),
          emi_amount: numOrUndefined(emiAmount),
        },
      };
    }
    return {};
  };

  const createMutation = useMutation({
    mutationFn: () =>
      walletsApi.create({
        name,
        type,
        provider: provider || undefined,
        account_last4: accountLast4 || undefined,
        opening_balance: Number(openingBalance) || 0,
        ...buildTypeDetails(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['wallets']});
      navigation.goBack();
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      walletsApi.update(walletId as string, {
        name,
        provider: provider || undefined,
        account_last4: accountLast4 || undefined,
        ...buildTypeDetails(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['wallets']});
      queryClient.invalidateQueries({queryKey: ['wallets', walletId]});
      navigation.goBack();
    },
  });

  const mutation = isEdit ? updateMutation : createMutation;
  const showLast4Toggle = accountLast4.length === 4;

  return (
    <ScrollView style={styles.container} contentContainerStyle={{padding: spacing.lg, paddingBottom: spacing.xl}}>
      {!isEdit && (
        <>
          <Text style={styles.sectionLabel}>Type</Text>
          <View style={styles.typeGrid}>
            {WALLET_TYPES.map((t) => (
              <Pressable key={t.value} style={[styles.typeTile, type === t.value && styles.typeTileSelected]} onPress={() => setType(t.value)}>
                <Text style={[styles.typeGlyph, type === t.value && {color: colors.accentOnDark}]}>{t.glyph}</Text>
                <Text style={type === t.value ? styles.typeLabelSelected : styles.typeLabel}>{t.label}</Text>
              </Pressable>
            ))}
          </View>
        </>
      )}

      <View style={{gap: spacing.md, marginTop: spacing.lg}}>
        <Field label="Name">
          <TextInput style={styles.fieldInput} value={name} onChangeText={setName} placeholderTextColor={colors.textSecondary} placeholder="e.g. HDFC Savings" />
        </Field>
        <Field label="Provider">
          <TextInput style={styles.fieldInput} value={provider} onChangeText={setProvider} placeholderTextColor={colors.textSecondary} placeholder="e.g. HDFC Bank" />
        </Field>
        <Field label="Last 4 digits">
          <TextInput
            style={[styles.fieldInput, styles.fieldInputMono]}
            value={accountLast4}
            onChangeText={setAccountLast4}
            keyboardType="number-pad"
            maxLength={4}
            placeholder="4821"
            placeholderTextColor={colors.textSecondary}
          />
        </Field>

        {!isEdit && (
          <Field label="Opening balance">
            <TextInput
              style={[styles.fieldInput, styles.fieldInputMono]}
              value={openingBalance}
              onChangeText={setOpeningBalance}
              keyboardType="numeric"
              placeholderTextColor={colors.textSecondary}
            />
          </Field>
        )}

        {type === 'credit_card' && (
          <>
            <View style={styles.fieldRow}>
              <View style={{flex: 1}}>
                <Field label="Credit limit">
                  <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={creditLimit} onChangeText={setCreditLimit} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
                </Field>
              </View>
              <View style={{flex: 1}}>
                <Field label="Min due %">
                  <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={minDuePercent} onChangeText={setMinDuePercent} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
                </Field>
              </View>
            </View>
            <View style={styles.fieldRow}>
              <View style={{flex: 1}}>
                <Field label="Statement day">
                  <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={statementDay} onChangeText={setStatementDay} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />
                </Field>
              </View>
              <View style={{flex: 1}}>
                <Field label="Due day">
                  <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={dueDay} onChangeText={setDueDay} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />
                </Field>
              </View>
            </View>
          </>
        )}

        {type === 'pay_later' && (
          <View style={styles.fieldRow}>
            <View style={{flex: 1}}>
              <Field label="Credit limit">
                <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={creditLimit} onChangeText={setCreditLimit} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
              </Field>
            </View>
            <View style={{flex: 1}}>
              <Field label="Due day">
                <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={dueDay} onChangeText={setDueDay} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />
              </Field>
            </View>
          </View>
        )}

        {type === 'loan' && (
          <>
            <View style={styles.fieldRow}>
              <View style={{flex: 1}}>
                <Field label="Principal">
                  <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={principal} onChangeText={setPrincipal} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
                </Field>
              </View>
              <View style={{flex: 1}}>
                <Field label="Interest %">
                  <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={interestRate} onChangeText={setInterestRate} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
                </Field>
              </View>
            </View>
            <View style={styles.fieldRow}>
              <View style={{flex: 1}}>
                <Field label="Tenure (months)">
                  <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={tenureMonths} onChangeText={setTenureMonths} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />
                </Field>
              </View>
              <View style={{flex: 1}}>
                <Field label="EMI amount">
                  <TextInput style={[styles.fieldInput, styles.fieldInputMono]} value={emiAmount} onChangeText={setEmiAmount} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
                </Field>
              </View>
            </View>
          </>
        )}

        {showLast4Toggle && (
          <View style={styles.toggleRow}>
            <View style={{flex: 1}}>
              <Text style={styles.toggleTitle}>Match bank SMS to this card</Text>
              <Text style={styles.toggleSubtitle}>Uses the last 4 digits.</Text>
            </View>
            <View style={[styles.toggleTrack, styles.toggleTrackOn]}>
              <View style={styles.toggleThumb} />
            </View>
          </View>
        )}
      </View>

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending || !name.trim()}>
        <Text style={styles.buttonText}>{mutation.isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Save wallet'}</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  sectionLabel: {fontSize: 11, letterSpacing: 1, textTransform: 'uppercase', color: '#5A5A66', marginBottom: spacing.sm},
  typeGrid: {flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs},
  typeTile: {
    width: '31%',
    padding: 12,
    borderRadius: 14,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    gap: 7,
  },
  typeTileSelected: {backgroundColor: 'rgba(91,84,249,.12)', borderColor: colors.accent},
  typeGlyph: {fontSize: 17, color: colors.textSecondary, fontFamily: fontFamilies.monetary},
  typeLabel: {fontSize: 11.5, color: '#C9C9D2'},
  typeLabelSelected: {fontSize: 11.5, fontWeight: '600', color: colors.textPrimary},
  field: {gap: spacing.xs},
  fieldLabel: {fontSize: 11, letterSpacing: 0.5, textTransform: 'uppercase', color: colors.textSecondary},
  fieldInput: {
    height: 50,
    borderRadius: radius.input,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    paddingHorizontal: 14,
    fontSize: 14,
  },
  fieldInputMono: {fontFamily: fontFamilies.monetary},
  fieldRow: {flexDirection: 'row', gap: spacing.sm},
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 13,
    borderRadius: radius.row,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  toggleTitle: {fontSize: 12.5, fontWeight: '600', color: colors.textPrimary},
  toggleSubtitle: {fontSize: 11, color: colors.textSecondary, marginTop: 2},
  toggleTrack: {width: 44, height: 26, borderRadius: radius.pill, padding: 3, justifyContent: 'center'},
  toggleTrackOn: {backgroundColor: colors.accent, alignItems: 'flex-end'},
  toggleThumb: {width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff'},
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center', marginTop: spacing.lg},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  error: {color: colors.negative, marginTop: spacing.sm},
});

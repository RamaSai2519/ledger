import React, {useState} from 'react';
import {Pressable, ScrollView, StyleSheet, Text, TextInput, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {WalletType} from '@/api/client';
import {walletsApi} from '@/api/client';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'WalletForm'>;

const WALLET_TYPES: {value: WalletType; label: string}[] = [
  {value: 'bank_account', label: 'Bank account'},
  {value: 'cash', label: 'Cash'},
  {value: 'credit_card', label: 'Credit card'},
  {value: 'pay_later', label: 'Pay later'},
  {value: 'loan', label: 'Loan'},
];

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

  // credit_card / pay_later / loan detail fields
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

  return (
    <ScrollView style={styles.container} contentContainerStyle={{paddingBottom: spacing.xl}}>
      <Text style={styles.title}>{isEdit ? 'Edit wallet' : 'Add wallet'}</Text>

      <Text style={styles.label}>Name</Text>
      <TextInput style={styles.input} value={name} onChangeText={setName} placeholderTextColor={colors.textSecondary} placeholder="e.g. HDFC Savings" />

      {!isEdit && (
        <>
          <Text style={styles.label}>Type</Text>
          <View style={styles.typeRow}>
            {WALLET_TYPES.map((t) => (
              <Pressable
                key={t.value}
                style={[styles.typeChip, type === t.value && styles.typeChipSelected]}
                onPress={() => setType(t.value)}>
                <Text style={type === t.value ? styles.typeChipTextSelected : styles.typeChipText}>{t.label}</Text>
              </Pressable>
            ))}
          </View>
        </>
      )}

      <Text style={styles.label}>Provider</Text>
      <TextInput style={styles.input} value={provider} onChangeText={setProvider} placeholderTextColor={colors.textSecondary} placeholder="e.g. HDFC Bank" />

      <Text style={styles.label}>Last 4 digits</Text>
      <TextInput
        style={styles.input}
        value={accountLast4}
        onChangeText={setAccountLast4}
        keyboardType="number-pad"
        maxLength={4}
        placeholderTextColor={colors.textSecondary}
      />

      {!isEdit && (
        <>
          <Text style={styles.label}>Opening balance</Text>
          <TextInput
            style={styles.input}
            value={openingBalance}
            onChangeText={setOpeningBalance}
            keyboardType="numeric"
            placeholderTextColor={colors.textSecondary}
          />
        </>
      )}

      {type === 'credit_card' && (
        <>
          <Text style={styles.sectionLabel}>Credit card details</Text>
          <TextInput style={styles.input} placeholder="Credit limit" value={creditLimit} onChangeText={setCreditLimit} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
          <TextInput style={styles.input} placeholder="Statement day (1-28)" value={statementDay} onChangeText={setStatementDay} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />
          <TextInput style={styles.input} placeholder="Due day (1-28)" value={dueDay} onChangeText={setDueDay} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />
          <TextInput style={styles.input} placeholder="Min due %" value={minDuePercent} onChangeText={setMinDuePercent} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
        </>
      )}

      {type === 'pay_later' && (
        <>
          <Text style={styles.sectionLabel}>Pay later details</Text>
          <TextInput style={styles.input} placeholder="Credit limit" value={creditLimit} onChangeText={setCreditLimit} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
          <TextInput style={styles.input} placeholder="Billing cycle day" value={billingCycleDay} onChangeText={setBillingCycleDay} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />
          <TextInput style={styles.input} placeholder="Due day" value={dueDay} onChangeText={setDueDay} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />
        </>
      )}

      {type === 'loan' && (
        <>
          <Text style={styles.sectionLabel}>Loan details</Text>
          <TextInput style={styles.input} placeholder="Principal" value={principal} onChangeText={setPrincipal} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
          <TextInput style={styles.input} placeholder="Interest rate %" value={interestRate} onChangeText={setInterestRate} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
          <TextInput style={styles.input} placeholder="Tenure (months)" value={tenureMonths} onChangeText={setTenureMonths} keyboardType="number-pad" placeholderTextColor={colors.textSecondary} />
          <TextInput style={styles.input} placeholder="EMI amount" value={emiAmount} onChangeText={setEmiAmount} keyboardType="numeric" placeholderTextColor={colors.textSecondary} />
        </>
      )}

      {mutation.isError && <Text style={styles.error}>{(mutation.error as Error).message}</Text>}

      <Pressable style={styles.button} onPress={() => mutation.mutate()} disabled={mutation.isPending || !name.trim()}>
        <Text style={styles.buttonText}>
          {mutation.isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Create wallet'}
        </Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  title: {color: colors.textPrimary, fontSize: 22, fontWeight: '600', marginBottom: spacing.lg},
  label: {color: colors.textSecondary, fontSize: 13, marginBottom: spacing.xs, marginTop: spacing.sm},
  sectionLabel: {color: colors.textPrimary, fontSize: 14, fontWeight: '600', marginTop: spacing.md, marginBottom: spacing.xs},
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  typeRow: {flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs, marginBottom: spacing.sm},
  typeChip: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
  },
  typeChipSelected: {backgroundColor: colors.accent, borderColor: colors.accent},
  typeChipText: {color: colors.textSecondary, fontSize: 13},
  typeChipTextSelected: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  button: {backgroundColor: colors.accent, borderRadius: radius.pill, padding: spacing.md, alignItems: 'center', marginTop: spacing.lg},
  buttonText: {color: colors.textPrimary, fontWeight: '600'},
  error: {color: colors.negative, marginTop: spacing.sm},
});

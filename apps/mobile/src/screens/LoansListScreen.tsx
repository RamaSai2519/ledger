import React from 'react';
import {FlatList, Pressable, StyleSheet, Text, View} from 'react-native';
import {useQuery} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {Loan} from '@/api/client';
import {loansApi} from '@/api/client';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'LoansList'>;

// No screen for this exists in the design project (LED-14 came after the
// mockup catalog) — styled to match RecurringRulesListScreen's card/row
// language (radius.row surfaces, monetary-mono amounts) rather than left
// unstyled.
function LoanCard({loan, onPress}: {loan: Loan; onPress: () => void}) {
  return (
    <Pressable style={[styles.card, !loan.is_active && {opacity: 0.55}]} onPress={onPress}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardName}>{loan.name}</Text>
        <Text style={styles.cardAmount}>₹{loan.outstanding_balance.toLocaleString('en-IN')}</Text>
      </View>
      <Text style={styles.cardMeta}>
        EMI ₹{loan.emi_amount.toLocaleString('en-IN')} · next{' '}
        {new Date(loan.next_due_date).toLocaleDateString('en-GB', {day: '2-digit', month: 'short'})}
        {!loan.is_active ? ' · closed' : ''}
      </Text>
    </Pressable>
  );
}

export function LoansListScreen({navigation}: Props) {
  const query = useQuery({queryKey: ['loans'], queryFn: () => loansApi.list()});
  const loans = query.data?.loans ?? [];

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Loans</Text>
        <Pressable onPress={() => navigation.navigate('LoanForm', undefined)} hitSlop={8}>
          <Text style={styles.addGlyph}>+</Text>
        </Pressable>
      </View>

      {query.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {query.isSuccess && loans.length === 0 && (
        <Text style={styles.stateText}>No loans yet — add one to track its EMI schedule and outstanding balance.</Text>
      )}

      <FlatList
        data={loans}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{padding: spacing.lg, gap: spacing.sm}}
        renderItem={({item}) => <LoanCard loan={item} onPress={() => navigation.navigate('LoanDetail', {loanId: item.id})} />}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  header: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 20, fontWeight: '600'},
  addGlyph: {color: colors.accentOnDark, fontSize: 24},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl, paddingHorizontal: spacing.lg, lineHeight: 20},
  card: {padding: 14, borderRadius: radius.row, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  cardHeader: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'},
  cardName: {color: colors.textPrimary, fontSize: 13.5, fontWeight: '600'},
  cardAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 13.5},
  cardMeta: {color: colors.textSecondary, fontSize: 11.5, marginTop: 4},
});

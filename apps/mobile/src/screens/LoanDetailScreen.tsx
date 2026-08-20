import React, {useLayoutEffect} from 'react';
import {Pressable, ScrollView, StyleSheet, Text, View} from 'react-native';
import {useQuery} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import type {RootStackParamList} from '@/navigation/types';
import {loansApi, transactionsApi} from '@/api/client';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'LoanDetail'>;

export function LoanDetailScreen({route, navigation}: Props) {
  const {loanId} = route.params;

  // No GET /loans/<id> on the backend (mirrors recurring_rules) — fetch via
  // list() and find, same pattern LoanFormScreen uses.
  const loanQuery = useQuery({
    queryKey: ['loans', loanId],
    queryFn: async () => (await loansApi.list()).loans.find((l) => l.id === loanId),
  });
  // Payment history: transactions the EMI job created against this loan,
  // queryable via GET /transactions?loan_id=... (LED-14).
  const paymentsQuery = useQuery({
    queryKey: ['transactions', {loan_id: loanId}],
    queryFn: () => transactionsApi.list({loan_id: loanId, page_size: 50}),
  });

  useLayoutEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <Pressable onPress={() => navigation.navigate('LoanForm', {loanId})} hitSlop={8}>
          <MaterialIcons name="edit" style={styles.headerActionIcon} />
        </Pressable>
      ),
    });
  }, [navigation, loanId]);

  if (loanQuery.isLoading) {
    return (
      <View style={styles.container}>
        <Text style={styles.stateText}>Loading loan…</Text>
      </View>
    );
  }

  const loan = loanQuery.data;
  if (!loan) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>Loan not found</Text>
      </View>
    );
  }

  const payments = paymentsQuery.data?.transactions ?? [];
  const progressPercent = loan.principal > 0 ? Math.min(100, 100 - (loan.outstanding_balance / loan.principal) * 100) : 0;

  return (
    <ScrollView style={styles.container} contentContainerStyle={{paddingBottom: spacing.xl}}>
      <View style={styles.heroCard}>
        <View style={styles.heroHeader}>
          <Text style={styles.heroName}>{loan.name}</Text>
          <View style={styles.heroBadge}>
            <Text style={styles.heroBadgeText}>{loan.is_active ? 'Active' : 'Closed'}</Text>
          </View>
        </View>
        <View style={styles.heroFooter}>
          <View>
            <Text style={styles.heroLabel}>Outstanding</Text>
            <Text style={styles.heroAmount}>₹{loan.outstanding_balance.toLocaleString('en-IN')}</Text>
          </View>
          <View style={{alignItems: 'flex-end'}}>
            <Text style={styles.heroLabel}>EMI</Text>
            <Text style={[styles.heroAmount, {fontSize: 15}]}>₹{loan.emi_amount.toLocaleString('en-IN')}</Text>
          </View>
        </View>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, {width: `${progressPercent}%`}]} />
        </View>
      </View>

      <View style={styles.statsRow}>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>Principal</Text>
          <Text style={styles.statValue}>₹{loan.principal.toLocaleString('en-IN')}</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>Interest rate</Text>
          <Text style={styles.statValue}>{loan.annual_interest_rate}%</Text>
        </View>
      </View>
      <View style={styles.statsRow}>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>Tenure</Text>
          <Text style={styles.statValue}>{loan.tenure_months} mo</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>{loan.is_active ? 'Next due' : 'Started'}</Text>
          <Text style={styles.statValue}>
            {new Date(loan.is_active ? loan.next_due_date : loan.start_date).toLocaleDateString('en-GB', {
              day: '2-digit',
              month: 'short',
              year: 'numeric',
            })}
          </Text>
        </View>
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Payment history</Text>
      </View>
      {paymentsQuery.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {paymentsQuery.isSuccess && payments.length === 0 && (
        <Text style={styles.stateText}>No EMI payments recorded yet.</Text>
      )}
      <View>
        {payments.map((txn) => (
          <View key={txn.id} style={styles.txnRow}>
            <View style={{flex: 1}}>
              <Text style={styles.txnMerchant}>{txn.note || 'EMI payment'}</Text>
              <Text style={styles.txnMeta}>{new Date(txn.date).toLocaleDateString('en-GB', {day: '2-digit', month: 'short', year: 'numeric'})}</Text>
            </View>
            <Text style={styles.txnAmount}>−₹{txn.amount.toLocaleString('en-IN')}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background, padding: spacing.lg},
  headerActionIcon: {fontSize: 20, color: colors.textSecondary, marginRight: spacing.sm},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl},
  errorText: {color: colors.negative, textAlign: 'center', marginTop: spacing.xl},
  heroCard: {padding: 18, borderRadius: radius.card, backgroundColor: colors.accent},
  heroHeader: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'},
  heroName: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  heroBadge: {paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.pill, backgroundColor: 'rgba(255,255,255,.16)'},
  heroBadgeText: {color: colors.textPrimary, fontSize: 10},
  heroFooter: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: spacing.lg},
  heroLabel: {color: 'rgba(255,255,255,.75)', fontSize: 10.5},
  heroAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 24, marginTop: 4},
  progressTrack: {height: 5, borderRadius: 3, backgroundColor: 'rgba(255,255,255,.2)', overflow: 'hidden', marginTop: spacing.md},
  progressFill: {height: '100%', borderRadius: 3, backgroundColor: '#fff'},
  statsRow: {flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm},
  statCard: {flex: 1, padding: 13, borderRadius: radius.row, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  statLabel: {fontSize: 10.5, color: colors.textSecondary},
  statValue: {fontFamily: fontFamilies.monetary, fontSize: 15, marginTop: 5, color: colors.textPrimary},
  sectionHeader: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingTop: spacing.lg, paddingBottom: 4},
  sectionTitle: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 14, fontWeight: '600'},
  txnRow: {flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.border},
  txnMerchant: {color: colors.textPrimary, fontSize: 13, fontWeight: '500'},
  txnMeta: {color: colors.textSecondary, fontSize: 11, marginTop: 1},
  txnAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 13.5},
});

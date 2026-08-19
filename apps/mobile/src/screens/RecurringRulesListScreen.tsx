import React from 'react';
import {FlatList, Pressable, StyleSheet, Text, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {RecurringRule} from '@/api/client';
import {recurringApi} from '@/api/client';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'RecurringRulesList'>;

const FREQUENCY_LABEL: Record<RecurringRule['frequency'], string> = {weekly: 'Weekly', monthly: 'Monthly', yearly: 'Yearly'};

// No screen for this exists in the design project (it wasn't part of the
// mockup catalog) — styled to match the rest of the app's card/row language
// (radius.row surfaces, monetary-mono amounts) rather than left unstyled.
function RuleCard({rule, onPress, onSkip}: {rule: RecurringRule; onPress: () => void; onSkip: () => void}) {
  return (
    <Pressable style={[styles.card, !rule.is_active && {opacity: 0.55}]} onPress={onPress}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardName}>{rule.merchant_name}</Text>
        <Text style={styles.cardAmount}>{rule.amount != null ? `₹${rule.amount.toLocaleString('en-IN')}` : 'Varies'}</Text>
      </View>
      <Text style={styles.cardMeta}>
        {FREQUENCY_LABEL[rule.frequency]} · next {new Date(rule.next_due_date).toLocaleDateString('en-GB', {day: '2-digit', month: 'short'})}
        {rule.auto_create ? ' · auto-adds' : ' · reminds you'}
      </Text>
      <Pressable style={styles.skipButton} onPress={onSkip}>
        <Text style={styles.skipButtonText}>Skip next</Text>
      </Pressable>
    </Pressable>
  );
}

export function RecurringRulesListScreen({navigation}: Props) {
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ['recurring'], queryFn: () => recurringApi.list()});

  const skipMutation = useMutation({
    mutationFn: (id: string) => recurringApi.skipNext(id),
    onSuccess: () => queryClient.invalidateQueries({queryKey: ['recurring']}),
  });

  const rules = query.data?.recurring_rules ?? [];

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Recurring</Text>
        <Pressable onPress={() => navigation.navigate('RecurringRuleForm', undefined)} hitSlop={8}>
          <Text style={styles.addGlyph}>+</Text>
        </Pressable>
      </View>

      {query.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {query.isSuccess && rules.length === 0 && (
        <Text style={styles.stateText}>
          No recurring rules yet — mark a transaction as recurring, or add one here (rent, subscriptions, EMIs).
        </Text>
      )}

      <FlatList
        data={rules}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{padding: spacing.lg, gap: spacing.sm}}
        renderItem={({item}) => (
          <RuleCard
            rule={item}
            onPress={() => navigation.navigate('RecurringRuleForm', {ruleId: item.id})}
            onSkip={() => skipMutation.mutate(item.id)}
          />
        )}
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
  skipButton: {alignSelf: 'flex-start', marginTop: spacing.sm},
  skipButtonText: {color: colors.accentOnDark, fontSize: 11.5, fontWeight: '600'},
});

import React from 'react';
import {FlatList, Pressable, ScrollView, StyleSheet, Text, View} from 'react-native';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import {useMutation, useQueries, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {Category, Wallet} from '@/api/client';
import type {Budget} from '@/api/client';
import {budgetsApi, categoriesApi, insightsApi, notificationsApi, smsApi, transactionsApi, walletsApi} from '@/api/client';
import {BottomNavBar} from '@/components/BottomNavBar';
import {Sparkline} from '@/components/InsightBars';
import {WalletCardStack} from '@/components/WalletCardStack';
import {Skeleton, SkeletonRow} from '@/components/Skeleton';
import {SmsSuggestionSheet} from '@/components/SmsSuggestionSheet';
import {categoryHues, colors, fontFamilies, radius, spacing} from '@/theme/tokens';
import {glyphForCategoryIcon} from '@/theme/categoryIcons';
import {useAuthStore} from '@/state/authStore';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

const LIABILITY_TYPES = new Set<Wallet['type']>(['credit_card', 'pay_later', 'loan']);
const BUDGET_BAR_COLORS = [colors.accent, colors.positive, categoryHues.travel, categoryHues.rent];

function computeNetWorth(wallets: Wallet[]): number {
  return wallets.reduce((sum, w) => {
    if (w.is_archived) return sum;
    return LIABILITY_TYPES.has(w.type) ? sum - w.current_balance : sum + w.current_balance;
  }, 0);
}

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function BudgetStrip({navigation}: {navigation: Props['navigation']}) {
  const budgetsQuery = useQuery({queryKey: ['budgets'], queryFn: () => budgetsApi.list()});
  const budgets = budgetsQuery.data?.budgets ?? [];
  const categoriesQuery = useQuery({queryKey: ['categories', 'all'], queryFn: () => categoriesApi.list()});

  const progressQueries = useQueries({
    queries: budgets.map((b) => ({
      queryKey: ['budgets', b.id, 'progress'],
      queryFn: () => budgetsApi.progress(b.id),
      enabled: budgets.length > 0,
    })),
  });

  if (budgetsQuery.isLoading || budgets.length === 0) return null;

  const totalSpent = progressQueries.reduce((s, q) => s + (q.data?.spent ?? 0), 0);
  const totalAmount = progressQueries.reduce((s, q) => s + (q.data?.amount ?? 0), 0);
  const labelFor = (b: Budget) => {
    if (b.scope === 'overall') return 'Overall';
    const cat = categoriesQuery.data?.categories.find((c) => c.id === b.scope_ref_id);
    return cat?.name ?? b.scope;
  };

  return (
    <Pressable style={styles.card} onPress={() => navigation.navigate('BudgetsList')}>
      <View style={styles.budgetHeader}>
        <Text style={styles.cardTitle}>{new Date().toLocaleDateString('en-IN', {month: 'long'})} budget</Text>
        <Text style={styles.budgetTotal}>
          ₹{totalSpent.toLocaleString('en-IN')} <Text style={styles.budgetTotalMuted}>/ {totalAmount.toLocaleString('en-IN')}</Text>
        </Text>
      </View>
      <View style={styles.budgetBars}>
        {budgets.slice(0, 3).map((b, i) => {
          const progress = progressQueries[i]?.data;
          const percent = Math.min(100, progress?.percent ?? 0);
          const over = (progress?.percent ?? 0) >= 100;
          return (
            <View key={b.id} style={{flex: 1, gap: 5}}>
              <View style={styles.budgetTrack}>
                <View style={[styles.budgetFill, {width: `${percent}%`, backgroundColor: over ? colors.negative : BUDGET_BAR_COLORS[i]}]} />
              </View>
              <Text style={[styles.budgetLabel, over && {color: colors.negative}]} numberOfLines={1}>
                {labelFor(b)} {over ? 'over' : `${percent.toFixed(0)}%`}
              </Text>
            </View>
          );
        })}
      </View>
    </Pressable>
  );
}

function ConfirmToast({merchant, amount}: {merchant: string; amount: number}) {
  return (
    <View style={styles.toast}>
      <MaterialIcons name="check-circle" style={styles.toastIcon} />
      <Text style={styles.toastText}>
        Added ₹{amount.toFixed(0)} at {merchant}
      </Text>
    </View>
  );
}

// s22/s23 in the design project — a fresh suggestion first arrives as the
// slide-up sheet (the "signature moment"); once seen (dismissed without
// acting, or the app is reopened later with it still pending) it falls back
// to this persistent inline card so it's never lost. `seenIds` is
// session-local (a ref, not persisted) — each suggestion still only
// interrupts with the sheet once per app session.
function SmsSuggestionInlineCard({navigation}: {navigation: Props['navigation']}) {
  const queryClient = useQueryClient();
  const suggestionsQuery = useQuery({queryKey: ['sms', 'suggestions'], queryFn: () => smsApi.suggestions()});
  const suggestion = suggestionsQuery.data?.suggestions[0];

  const seenIds = React.useRef(new Set<string>());
  const [sheetSuggestionId, setSheetSuggestionId] = React.useState<string | null>(null);
  const [toast, setToast] = React.useState<{merchant: string; amount: number} | null>(null);

  React.useEffect(() => {
    if (suggestion && !seenIds.current.has(suggestion.id)) {
      seenIds.current.add(suggestion.id);
      setSheetSuggestionId(suggestion.id);
    }
  }, [suggestion]);

  React.useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(timer);
  }, [toast]);

  const invalidate = () => {
    queryClient.invalidateQueries({queryKey: ['sms', 'suggestions']});
    queryClient.invalidateQueries({queryKey: ['transactions']});
    queryClient.invalidateQueries({queryKey: ['wallets']});
  };
  const confirmMutation = useMutation({
    mutationFn: () => smsApi.accept(suggestion!.id),
    onSuccess: () => {
      setToast({merchant: suggestion!.parsed_merchant ?? 'a merchant', amount: suggestion!.parsed_amount ?? 0});
      setSheetSuggestionId(null);
      invalidate();
    },
  });
  const dismissMutation = useMutation({mutationFn: () => smsApi.dismiss(suggestion!.id), onSuccess: invalidate});

  return (
    <>
      <SmsSuggestionSheet
        visible={!!suggestion && sheetSuggestionId === suggestion.id}
        suggestion={suggestion ?? null}
        canConfirm={!!(suggestion?.suggested_wallet_id && suggestion?.suggested_category_id)}
        confirming={confirmMutation.isPending}
        onConfirm={() => confirmMutation.mutate()}
        onEdit={() => {
          setSheetSuggestionId(null);
          navigation.navigate('SmsSuggestionEdit', {suggestion: suggestion!});
        }}
        onDismiss={() => {
          setSheetSuggestionId(null);
          dismissMutation.mutate();
        }}
        onRequestClose={() => setSheetSuggestionId(null)}
      />
      {toast && <ConfirmToast merchant={toast.merchant} amount={toast.amount} />}
      {suggestion && sheetSuggestionId !== suggestion.id && (
        <View style={styles.smsCard}>
          <View style={styles.smsHeader}>
            <MaterialIcons name="sms" style={styles.smsGlyph} />
            <Text style={styles.smsLabel}>Detected from SMS</Text>
          </View>
          <Text style={styles.smsBody}>
            ₹{(suggestion.parsed_amount ?? 0).toFixed(0)} at {suggestion.parsed_merchant ?? 'a merchant'} — add as{' '}
            {suggestion.parsed_direction === 'credit' ? 'income' : 'an expense'}?
          </Text>
          <View style={styles.smsActions}>
            <Pressable
              style={[
                styles.smsConfirm,
                (!(suggestion.suggested_wallet_id && suggestion.suggested_category_id) || confirmMutation.isPending) && {opacity: 0.5},
              ]}
              disabled={!(suggestion.suggested_wallet_id && suggestion.suggested_category_id) || confirmMutation.isPending}
              onPress={() => confirmMutation.mutate()}>
              <Text style={styles.smsConfirmText}>{confirmMutation.isPending ? 'Confirming…' : 'Confirm'}</Text>
            </Pressable>
            <Pressable style={styles.smsEdit} onPress={() => navigation.navigate('SmsSuggestionEdit', {suggestion})}>
              <Text style={styles.smsEditText}>Edit</Text>
            </Pressable>
            <Pressable style={styles.smsDismiss} onPress={() => dismissMutation.mutate()}>
              <Text style={styles.smsDismissText}>Dismiss</Text>
            </Pressable>
          </View>
        </View>
      )}
    </>
  );
}

function TransactionRow({txn, category}: {txn: import('@/api/client').Transaction; category?: Category}) {
  const isExpense = txn.type === 'expense';
  return (
    <View style={styles.txnRow}>
      <View style={styles.txnIconTile}>
        <MaterialCommunityIcons name={glyphForCategoryIcon(category?.icon)} size={16} color="#C9C9D2" />
        <View style={[styles.txnDot, {backgroundColor: category?.color ?? colors.accent}]} />
      </View>
      <View style={{flex: 1}}>
        <Text style={styles.txnMerchant}>{txn.merchant_name || txn.note || txn.type}</Text>
        <Text style={styles.txnMeta}>{category?.name ?? txn.type}</Text>
      </View>
      <Text style={[styles.txnAmount, txn.type === 'income' && {color: colors.positive}]}>
        {isExpense ? '−' : txn.type === 'income' ? '+' : ''}₹{txn.amount.toLocaleString('en-IN')}
      </Text>
    </View>
  );
}

export function HomeScreen({navigation}: Props) {
  const name = useAuthStore((s) => s.name);
  const queryClient = useQueryClient();

  const unreadQuery = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: () => notificationsApi.list({user_id: 'me', is_read: 'false', page_size: 1}),
  });
  const unreadCount = unreadQuery.data?.total ?? 0;

  React.useEffect(() => {
    // Re-check the unread count whenever Home regains focus (e.g. coming
    // back from the Notifications screen after reading/dismissing some),
    // so the badge clears without waiting for its own background refetch.
    const unsubscribe = navigation.addListener('focus', () => {
      queryClient.invalidateQueries({queryKey: ['notifications']});
    });
    return unsubscribe;
  }, [navigation, queryClient]);

  const walletsQuery = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});
  const transactionsQuery = useQuery({
    queryKey: ['transactions', 'recent'],
    queryFn: () => transactionsApi.list({page: 1, page_size: 10}),
  });
  const categoriesQuery = useQuery({queryKey: ['categories', 'all'], queryFn: () => categoriesApi.list()});
  const netWorthHistoryQuery = useQuery({
    queryKey: ['insights', 'net-worth-history', 'home'],
    queryFn: () => insightsApi.netWorthHistory(),
  });

  const wallets = walletsQuery.data?.wallets.filter((w) => !w.is_archived) ?? [];
  const netWorth = computeNetWorth(wallets);
  const sparklinePoints = (
    netWorthHistoryQuery.data?.snapshots.slice(-6) ??
    Array.from({length: 6}, (_, i) => ({date: null as string | null, net_worth: 0}))
  ).map((s) => ({
    label: s.date ? new Date(s.date).toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}) : '',
    value: s.net_worth,
  }));

  const categoryById = new Map((categoriesQuery.data?.categories ?? []).map((c) => [c.id, c]));
  const todaysTransactions = (transactionsQuery.data?.transactions ?? []).filter((t) => {
    const d = new Date(t.date);
    const now = new Date();
    return d.toDateString() === now.toDateString();
  });
  const todaysExpense = todaysTransactions.filter((t) => t.type === 'expense').reduce((s, t) => s + t.amount, 0);

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={{paddingBottom: 8}}>
        <View style={styles.topBar}>
          <View style={styles.topBarLeft}>
            <View style={styles.mark}>
              <Text style={styles.markText}>L</Text>
            </View>
            <Text style={styles.greeting}>
              {greeting()}, {name}
            </Text>
          </View>
          <Pressable style={styles.bellWrap} onPress={() => navigation.navigate('Notifications')}>
            <MaterialIcons name="notifications" style={styles.bellGlyph} />
            {unreadCount > 0 && (
              <View style={styles.bellBadge}>
                <Text style={styles.bellBadgeText}>{unreadCount > 9 ? '9+' : unreadCount}</Text>
              </View>
            )}
          </Pressable>
        </View>

        <View style={styles.netWorthBlock}>
          <Text style={styles.netWorthLabel}>Net worth</Text>
          {walletsQuery.isLoading ? (
            <Skeleton style={styles.netWorthSkeleton} />
          ) : (
            <Text style={[styles.netWorthAmount, walletsQuery.isError && {opacity: 0.5}]}>
              ₹{netWorth.toLocaleString('en-IN')}
            </Text>
          )}
          {!walletsQuery.isLoading && (
            <View style={[styles.netWorthChart, walletsQuery.isError && {opacity: 0.5}]}>
              <Sparkline points={sparklinePoints} color={colors.accent} />
            </View>
          )}
        </View>

        {walletsQuery.isError && (
          <View style={styles.errorCard}>
            <MaterialIcons name="cloud-off" style={styles.errorIcon} />
            <View style={{flex: 1}}>
              <Text style={styles.errorTitle}>Can't reach the server</Text>
              <Text style={styles.errorSubtitle}>Showing figures from your last sync — new entries save on this phone and sync later.</Text>
              <Pressable onPress={() => walletsQuery.refetch()}>
                <Text style={styles.errorRetry}>Try again</Text>
              </Pressable>
            </View>
          </View>
        )}

        {walletsQuery.isSuccess && wallets.length === 0 && (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyTitle}>No wallets yet</Text>
            <Text style={styles.emptySubtitle}>Add your first bank account or card and your balance shows up here.</Text>
            <Pressable style={styles.emptyCta} onPress={() => navigation.navigate('WalletForm', undefined)}>
              <Text style={styles.emptyCtaText}>Add a wallet</Text>
            </Pressable>
          </View>
        )}

        <WalletCardStack wallets={wallets} />

        <BudgetStrip navigation={navigation} />
        <SmsSuggestionInlineCard navigation={navigation} />

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Today</Text>
          <Text style={styles.sectionMeta}>−₹{todaysExpense.toLocaleString('en-IN')}</Text>
        </View>

        {transactionsQuery.isLoading && (
          <View style={{paddingHorizontal: spacing.lg}}>
            <SkeletonRow />
            <SkeletonRow />
          </View>
        )}
        {transactionsQuery.isSuccess && todaysTransactions.length === 0 && (
          <Text style={styles.emptyText}>No transactions yet today — tap + to add your first one.</Text>
        )}
        <FlatList
          data={todaysTransactions}
          keyExtractor={(item) => item.id}
          scrollEnabled={false}
          contentContainerStyle={{paddingHorizontal: spacing.lg, gap: 2}}
          renderItem={({item}) => (
            <Pressable onPress={() => navigation.navigate('TransactionForm', {transactionId: item.id})}>
              <TransactionRow txn={item} category={item.category_id ? categoryById.get(item.category_id) : undefined} />
            </Pressable>
          )}
        />
      </ScrollView>
      <BottomNavBar active="home" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  topBar: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  topBarLeft: {flexDirection: 'row', alignItems: 'center', gap: spacing.sm},
  mark: {width: 30, height: 30, borderRadius: 10, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  markText: {color: colors.textPrimary, fontFamily: fontFamilies.displayBold, fontSize: 15},
  greeting: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  bellWrap: {position: 'relative'},
  bellGlyph: {fontSize: 18},
  bellBadge: {
    position: 'absolute',
    top: -4,
    right: -6,
    minWidth: 15,
    height: 15,
    borderRadius: 8,
    paddingHorizontal: 3,
    backgroundColor: colors.negative,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: colors.background,
  },
  bellBadgeText: {color: colors.textPrimary, fontSize: 9, fontWeight: '700', lineHeight: 11},
  netWorthBlock: {paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  netWorthLabel: {fontSize: 11, letterSpacing: 0.9, textTransform: 'uppercase', color: colors.textSecondary},
  netWorthAmount: {
    color: colors.textPrimary,
    fontFamily: fontFamilies.display,
    fontSize: 34,
    letterSpacing: -1.1,
    lineHeight: 34,
    fontWeight: '600',
    marginTop: 6,
  },
  netWorthChart: {marginTop: spacing.sm},
  netWorthSkeleton: {width: 180, height: 34, marginTop: 6},
  card: {marginHorizontal: 16, marginTop: 4, padding: 16, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  cardTitle: {color: colors.textPrimary, fontSize: 12.5, fontWeight: '600'},
  budgetHeader: {flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between'},
  budgetTotal: {color: colors.textSecondary, fontFamily: fontFamilies.monetary, fontSize: 11.5},
  budgetTotalMuted: {color: '#73737F'},
  budgetBars: {flexDirection: 'row', gap: 6, marginTop: 10},
  budgetTrack: {height: 5, borderRadius: 3, backgroundColor: colors.border, overflow: 'hidden'},
  budgetFill: {height: '100%', borderRadius: 3},
  budgetLabel: {fontSize: 10, color: colors.textSecondary},
  smsCard: {marginHorizontal: 16, marginTop: 10, padding: 16, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderStyle: 'dashed', borderColor: '#3B3670'},
  smsHeader: {flexDirection: 'row', alignItems: 'center', gap: 8},
  smsGlyph: {color: colors.accentOnDark, fontSize: 17},
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginHorizontal: 16,
    marginTop: 10,
    padding: 12,
    borderRadius: 14,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: 'rgba(47,217,136,.35)',
  },
  toastIcon: {color: colors.positive, fontSize: 18},
  toastText: {color: colors.textPrimary, fontSize: 12.5, fontWeight: '600', flex: 1},
  smsLabel: {fontSize: 11, letterSpacing: 0.5, textTransform: 'uppercase', color: colors.accentOnDark, fontWeight: '600'},
  smsBody: {color: colors.textPrimary, fontSize: 13.5, fontWeight: '600', marginTop: 8, lineHeight: 18.5},
  smsActions: {flexDirection: 'row', gap: 8, marginTop: 11},
  smsConfirm: {flex: 1, height: 38, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  smsConfirmText: {color: colors.textPrimary, fontSize: 12.5, fontWeight: '600'},
  smsEdit: {height: 38, paddingHorizontal: 16, borderRadius: radius.pill, borderWidth: 1, borderColor: '#2A2A38', alignItems: 'center', justifyContent: 'center'},
  smsEditText: {color: '#C9C9D2', fontSize: 12.5},
  smsDismiss: {height: 38, paddingHorizontal: 14, alignItems: 'center', justifyContent: 'center'},
  smsDismissText: {color: colors.textSecondary, fontSize: 12.5},
  sectionHeader: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: 4},
  sectionTitle: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 14, fontWeight: '600'},
  sectionMeta: {color: colors.textSecondary, fontFamily: fontFamilies.monetary, fontSize: 11.5},
  stateText: {color: colors.textSecondary, fontSize: 13, paddingHorizontal: spacing.lg},
  emptyText: {color: colors.textSecondary, fontSize: 13, paddingHorizontal: spacing.lg, lineHeight: 19},
  errorCard: {
    flexDirection: 'row',
    gap: 12,
    marginHorizontal: 16,
    marginTop: spacing.sm,
    padding: 16,
    borderRadius: 18,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: 'rgba(255,107,107,.3)',
  },
  errorIcon: {color: colors.negative, fontSize: 22, marginTop: 2},
  errorTitle: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  errorSubtitle: {color: colors.textSecondary, fontSize: 11.5, marginTop: 4, lineHeight: 16},
  errorRetry: {color: colors.accentOnDark, fontSize: 12, fontWeight: '600', marginTop: spacing.sm},
  emptyCard: {marginHorizontal: 16, marginTop: spacing.sm, padding: 16, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  emptyTitle: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  emptySubtitle: {color: colors.textSecondary, fontSize: 11.5, marginTop: 4, lineHeight: 16},
  emptyCta: {alignSelf: 'flex-start', marginTop: spacing.sm, height: 38, paddingHorizontal: 16, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center'},
  emptyCtaText: {color: colors.textPrimary, fontSize: 12.5, fontWeight: '600'},
  txnRow: {flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 8},
  txnIconTile: {width: 36, height: 36, borderRadius: 12, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center'},
  txnIconGlyph: {color: '#C9C9D2', fontSize: 14, fontWeight: '700'},
  txnDot: {position: 'absolute', bottom: -2, right: -2, width: 11, height: 11, borderRadius: 6, borderWidth: 2, borderColor: colors.background},
  txnMerchant: {color: colors.textPrimary, fontSize: 13, fontWeight: '500'},
  txnMeta: {color: colors.textSecondary, fontSize: 11, marginTop: 1},
  txnAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 13.5},
});

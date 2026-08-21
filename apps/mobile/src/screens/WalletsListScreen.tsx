import React, {useState} from 'react';
import {FlatList, Pressable, StyleSheet, Text, View} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import {Swipeable} from 'react-native-gesture-handler';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import type {RootStackParamList} from '@/navigation/types';
import type {Wallet} from '@/api/client';
import {walletsApi} from '@/api/client';
import {BottomNavBar} from '@/components/BottomNavBar';
import {SkeletonRow} from '@/components/Skeleton';
import {colors, fontFamilies, radius, spacing} from '@/theme/tokens';
import {WALLET_TYPE_ICON} from '@/theme/walletIcons';

type Props = NativeStackScreenProps<RootStackParamList, 'WalletsList'>;

const WALLET_TYPE_LABELS: Record<Wallet['type'], string> = {
  bank_account: 'Bank account',
  credit_card: 'Credit card',
  pay_later: 'Pay later',
  cash: 'Cash',
};

const LIABILITY_TYPES = new Set<Wallet['type']>(['credit_card', 'pay_later']);

function getRemainingCredit(wallet: Wallet): number | null {
  const limit = wallet.type === 'credit_card' ? wallet.credit_card_details?.credit_limit : wallet.type === 'pay_later' ? wallet.pay_later_details?.credit_limit : undefined;
  return limit == null ? null : Math.max(0, limit - wallet.current_balance);
}

// Loans (LED-14) moved to their own dedicated LoansList screen — no longer
// a wallet filter here.
type FilterKey = 'all' | 'bank' | 'cards' | 'cash';
const FILTERS: Array<{key: FilterKey; label: string; types: Wallet['type'][] | null}> = [
  {key: 'all', label: 'All', types: null},
  {key: 'bank', label: 'Bank', types: ['bank_account']},
  {key: 'cards', label: 'Cards', types: ['credit_card', 'pay_later']},
  {key: 'cash', label: 'Cash', types: ['cash']},
];

// s40 in the design project — swipe-left reveal at −176px (two 88px
// actions), snapping open past −132px (react-native-gesture-handler's
// legacy `Swipeable`, not Reanimated — no reveal animation library is
// otherwise in the dependency tree, so this keeps the added surface area
// small). Reveals both Archive and Reconcile, matching the mock.
const SWIPE_ACTION_WIDTH = 88;
const SWIPE_SNAP_THRESHOLD = 132;

function WalletSwipeActions({onArchive, onReconcile}: {onArchive: () => void; onReconcile: () => void}) {
  return (
    <View style={styles.swipeActions}>
      <Pressable style={[styles.swipeAction, styles.swipeActionReconcile]} onPress={onReconcile}>
        <MaterialIcons name="rule" style={styles.swipeActionGlyph} />
        <Text style={styles.swipeActionText}>Reconcile</Text>
      </Pressable>
      <Pressable style={[styles.swipeAction, styles.swipeActionArchive]} onPress={onArchive}>
        <MaterialIcons name="archive" style={[styles.swipeActionGlyph, styles.swipeActionGlyphArchive]} />
        <Text style={[styles.swipeActionText, styles.swipeActionTextArchive]}>Archive</Text>
      </Pressable>
    </View>
  );
}

function WalletRow({wallet, navigation, onArchive}: {wallet: Wallet; navigation: Props['navigation']; onArchive: (id: string) => void}) {
  const isLiability = LIABILITY_TYPES.has(wallet.type);
  const remainingCredit = getRemainingCredit(wallet);
  const swipeableRef = React.useRef<Swipeable>(null);
  return (
    <Swipeable
      ref={swipeableRef}
      friction={2}
      rightThreshold={SWIPE_SNAP_THRESHOLD}
      overshootRight={false}
      renderRightActions={() => (
        <WalletSwipeActions
          onReconcile={() => {
            swipeableRef.current?.close();
            navigation.navigate('WalletReconcile', {walletId: wallet.id});
          }}
          onArchive={() => {
            swipeableRef.current?.close();
            onArchive(wallet.id);
          }}
        />
      )}>
      <Pressable
        style={[styles.row, isLiability && styles.rowLiability]}
        onPress={() => navigation.navigate('WalletDetail', {walletId: wallet.id})}>
        <View style={styles.rowIcon}>
          <MaterialIcons name={WALLET_TYPE_ICON[wallet.type]} style={[styles.rowIconGlyph, isLiability && {color: '#FF9B9B'}]} />
        </View>
        <View style={{flex: 1}}>
          <Text style={styles.rowName}>{wallet.name}</Text>
          <Text style={styles.rowMeta}>
            {wallet.account_last4 ? `•••• ${wallet.account_last4}` : WALLET_TYPE_LABELS[wallet.type]}
          </Text>
          {isLiability && remainingCredit != null && (
            <Text style={styles.rowCredit}>₹{remainingCredit.toLocaleString('en-IN')} limit left</Text>
          )}
        </View>
        <Text style={[styles.rowAmount, isLiability && {color: colors.negative}]}>
          ₹{Math.abs(wallet.current_balance).toLocaleString('en-IN')}
        </Text>
      </Pressable>
    </Swipeable>
  );
}

export function WalletsListScreen({navigation}: Props) {
  const [filter, setFilter] = useState<FilterKey>('all');
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ['wallets'], queryFn: () => walletsApi.list()});
  const archiveMutation = useMutation({
    mutationFn: (id: string) => walletsApi.archive(id),
    onSuccess: () => queryClient.invalidateQueries({queryKey: ['wallets']}),
  });

  const wallets = (query.data?.wallets ?? []).filter((w) => !w.is_archived);
  const activeFilter = FILTERS.find((f) => f.key === filter)!;
  const filtered = activeFilter.types ? wallets.filter((w) => activeFilter.types!.includes(w.type)) : wallets;

  const haveWallets = filtered.filter((w) => !LIABILITY_TYPES.has(w.type));
  const oweWallets = filtered.filter((w) => LIABILITY_TYPES.has(w.type));
  const totalHave = wallets.filter((w) => !LIABILITY_TYPES.has(w.type)).reduce((s, w) => s + w.current_balance, 0);
  const totalOwe = wallets.filter((w) => LIABILITY_TYPES.has(w.type)).reduce((s, w) => s + w.current_balance, 0);
  const totalRemainingCredit = wallets
    .filter((w) => LIABILITY_TYPES.has(w.type))
    .reduce((s, w) => s + (getRemainingCredit(w) ?? 0), 0);

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Wallets</Text>
        <Pressable onPress={() => navigation.navigate('WalletForm', undefined)} hitSlop={8}>
          <MaterialIcons name="add" style={styles.addGlyph} />
        </Pressable>
      </View>

      <View style={styles.chipRow}>
        {FILTERS.map((f) => (
          <Pressable key={f.key} style={[styles.chip, filter === f.key && styles.chipActive]} onPress={() => setFilter(f.key)}>
            <Text style={filter === f.key ? styles.chipTextActive : styles.chipText}>
              {f.key === 'all' ? `All ${wallets.length}` : f.label}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.splitRow}>
        <View style={[styles.splitCard]}>
          <Text style={styles.splitLabel}>You have</Text>
          <Text style={styles.splitAmount}>₹{totalHave.toLocaleString('en-IN')}</Text>
          {totalRemainingCredit > 0 && (
            <Text style={styles.splitSubtext}>+ ₹{totalRemainingCredit.toLocaleString('en-IN')} available credit</Text>
          )}
        </View>
        <View style={[styles.splitCard, styles.splitCardOwe]}>
          <Text style={styles.splitLabel}>You owe</Text>
          <Text style={[styles.splitAmount, {color: colors.negative}]}>₹{totalOwe.toLocaleString('en-IN')}</Text>
        </View>
      </View>

      {query.isLoading && (
        <View style={{paddingHorizontal: spacing.lg, marginTop: spacing.md}}>
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </View>
      )}
      {query.isError && (
        <View style={styles.errorBlock}>
          <MaterialIcons name="cloud-off" style={styles.errorIcon} />
          <Text style={styles.errorTitle}>Wallets didn't load</Text>
          <Text style={styles.errorSubtitle}>Check your connection and try again.</Text>
          <Pressable onPress={() => query.refetch()}>
            <Text style={styles.errorRetry}>Try again</Text>
          </Pressable>
        </View>
      )}
      {query.isSuccess && wallets.length === 0 && (
        <View style={styles.emptyBlock}>
          <Text style={styles.emptyTitle}>No wallets yet</Text>
          <Pressable style={styles.emptyOption} onPress={() => navigation.navigate('WalletForm', undefined)}>
            <Text style={styles.emptyOptionText}>Add a bank account</Text>
            <Text style={styles.emptyOptionChevron}>›</Text>
          </Pressable>
          <Pressable style={styles.emptyOption} onPress={() => navigation.navigate('WalletForm', undefined)}>
            <Text style={styles.emptyOptionText}>Add a credit card</Text>
            <Text style={styles.emptyOptionChevron}>›</Text>
          </Pressable>
          <Pressable style={styles.emptyOption} onPress={() => navigation.navigate('WalletForm', undefined)}>
            <Text style={styles.emptyOptionText}>Track cash only</Text>
            <Text style={styles.emptyOptionChevron}>›</Text>
          </Pressable>
        </View>
      )}

      <FlatList
        style={{flex: 1}}
        data={[
          ...(haveWallets.length ? [{type: 'header' as const, key: 'have-header', label: 'Money you have'}] : []),
          ...haveWallets.map((w) => ({type: 'wallet' as const, key: w.id, wallet: w})),
          ...(oweWallets.length ? [{type: 'header' as const, key: 'owe-header', label: 'Money you owe'}] : []),
          ...oweWallets.map((w) => ({type: 'wallet' as const, key: w.id, wallet: w})),
        ]}
        keyExtractor={(item) => item.key}
        contentContainerStyle={{paddingHorizontal: spacing.lg, paddingBottom: spacing.lg, gap: spacing.xs}}
        renderItem={({item}) =>
          item.type === 'header' ? (
            <Text style={styles.sectionLabel}>{item.label}</Text>
          ) : (
            <WalletRow wallet={item.wallet} navigation={navigation} onArchive={(id) => archiveMutation.mutate(id)} />
          )
        }
      />
      <BottomNavBar active="wallets" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  header: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  title: {color: colors.textPrimary, fontFamily: fontFamilies.display, fontSize: 20, fontWeight: '600'},
  addGlyph: {color: colors.accentOnDark, fontSize: 24},
  chipRow: {flexDirection: 'row', gap: 7, paddingHorizontal: spacing.lg, paddingTop: spacing.md},
  chip: {paddingHorizontal: 13, paddingVertical: 6, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border},
  chipActive: {backgroundColor: colors.textPrimary, borderColor: colors.textPrimary},
  chipText: {fontSize: 11.5, color: colors.textSecondary},
  chipTextActive: {fontSize: 11.5, fontWeight: '600', color: colors.background},
  splitRow: {flexDirection: 'row', gap: 10, paddingHorizontal: spacing.lg, paddingTop: spacing.md, marginBottom: spacing.md},
  splitCard: {flex: 1, padding: 13, borderRadius: radius.row, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  splitCardOwe: {borderColor: 'rgba(255,107,107,.3)'},
  splitLabel: {fontSize: 10.5, color: colors.textSecondary},
  splitAmount: {fontFamily: fontFamilies.monetary, fontSize: 16, marginTop: 5, color: colors.textPrimary},
  splitSubtext: {fontFamily: fontFamilies.monetary, fontSize: 10.5, marginTop: 3, color: colors.textSecondary},
  sectionLabel: {fontSize: 11, letterSpacing: 1, textTransform: 'uppercase', color: '#5A5A66', paddingTop: spacing.md, paddingBottom: 4},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl, paddingHorizontal: spacing.lg},
  errorBlock: {alignItems: 'center', marginTop: spacing.xl, gap: spacing.sm, paddingHorizontal: spacing.lg},
  errorIcon: {color: colors.negative, fontSize: 28},
  errorTitle: {color: colors.textPrimary, fontSize: 14, fontWeight: '600'},
  errorSubtitle: {color: colors.textSecondary, fontSize: 12.5, textAlign: 'center'},
  errorRetry: {color: colors.accentOnDark, fontSize: 12.5, fontWeight: '600'},
  emptyBlock: {marginHorizontal: spacing.lg, marginTop: spacing.lg, gap: spacing.sm},
  emptyTitle: {color: colors.textPrimary, fontSize: 15, fontWeight: '600', marginBottom: spacing.xs},
  emptyOption: {flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: radius.row, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  emptyOptionText: {flex: 1, color: colors.textPrimary, fontSize: 13},
  emptyOptionChevron: {color: colors.textSecondary, fontSize: 18},
  swipeActions: {flexDirection: 'row', marginLeft: 8, borderRadius: radius.row, overflow: 'hidden'},
  swipeAction: {width: SWIPE_ACTION_WIDTH, alignItems: 'center', justifyContent: 'center', gap: 4},
  swipeActionReconcile: {backgroundColor: colors.border},
  swipeActionArchive: {backgroundColor: 'rgba(255,107,107,.16)'},
  swipeActionGlyph: {fontSize: 19, color: colors.accentOnDark},
  swipeActionGlyphArchive: {color: '#FF9B9B'},
  swipeActionText: {color: colors.textPrimary, fontSize: 10, fontWeight: '600'},
  swipeActionTextArchive: {color: '#FF9B9B'},
  row: {flexDirection: 'row', alignItems: 'center', gap: 12, padding: 13, borderRadius: radius.row, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border},
  rowLiability: {borderWidth: 0, borderLeftWidth: 2, borderLeftColor: colors.negative},
  rowIcon: {width: 38, height: 38, borderRadius: 12, backgroundColor: colors.border, alignItems: 'center', justifyContent: 'center'},
  rowIconGlyph: {color: colors.accentOnDark, fontWeight: '700'},
  rowName: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  rowMeta: {color: colors.textSecondary, fontFamily: fontFamilies.monetary, fontSize: 11, marginTop: 2},
  rowCredit: {color: colors.positive, fontFamily: fontFamilies.monetary, fontSize: 10.5, marginTop: 2},
  rowAmount: {color: colors.textPrimary, fontFamily: fontFamilies.monetary, fontSize: 14},
});

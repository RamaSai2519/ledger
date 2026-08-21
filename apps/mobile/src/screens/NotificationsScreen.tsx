import React from 'react';
import {Pressable, ScrollView, StyleSheet, Text, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import MaterialIcons from 'react-native-vector-icons/MaterialIcons';
import type {RootStackParamList} from '@/navigation/types';
import type {Notification} from '@/api/client';
import {notificationsApi} from '@/api/client';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'Notifications'>;

const NEEDS_YOU_TYPES = new Set<Notification['type']>(['sms_suggestion', 'budget_threshold', 'budget_exceeded']);

const TYPE_GLYPH: Record<Notification['type'], string> = {
  sms_suggestion: 'sms',
  budget_threshold: 'donut-large',
  budget_exceeded: 'donut-large',
  digest: 'menu',
  bill_due: 'schedule',
  recurring_reminder: 'autorenew',
};

function summarize(notification: Notification): {title: string; meta: string} {
  const p = notification.payload;
  switch (notification.type) {
    case 'sms_suggestion':
      return {title: `₹${p.amount ?? '—'} at ${p.merchant ?? 'a merchant'}`, meta: 'Waiting for you to confirm'};
    case 'budget_threshold':
    case 'budget_exceeded':
      return {
        title: `${p.scope ?? 'Budget'} is ${notification.type === 'budget_exceeded' ? 'over' : 'nearing its limit'}`,
        meta: `${typeof p.percent === 'number' ? p.percent.toFixed(0) : p.percent}% used`,
      };
    case 'digest':
      return {title: `Spent ₹${p.total_spent ?? 0} so far`, meta: p.top_category ? `Top: ${p.top_category}` : 'Spending digest'};
    case 'bill_due':
      return {title: `${p.wallet_name ?? 'A bill'} due soon`, meta: `${p.due_date ?? ''}`};
    case 'recurring_reminder':
      return {title: `${p.merchant_name ?? 'Recurring transaction'} is due`, meta: p.amount ? `₹${p.amount}` : 'Confirm or skip'};
    default:
      return {title: 'New notification', meta: ''};
  }
}

function NotificationRow({notification, onPress, dim}: {notification: Notification; onPress: () => void; dim?: boolean}) {
  const {title, meta} = summarize(notification);
  const needsYou = NEEDS_YOU_TYPES.has(notification.type) && !notification.is_read;
  return (
    <Pressable style={[styles.row, needsYou && styles.rowNeedsYou, dim && {opacity: 0.72}]} onPress={onPress}>
      {!dim && <View style={[styles.dot, {backgroundColor: notification.is_read ? colors.border : colors.accent}]} />}
      <View style={{flex: 1}}>
        <Text style={dim ? styles.titleDim : styles.title}>{title}</Text>
        <Text style={styles.meta}>
          {meta} · {new Date(notification.created_at).toLocaleDateString()}
        </Text>
      </View>
      <MaterialIcons name={TYPE_GLYPH[notification.type] ?? 'circle'} style={styles.glyph} />
    </Pressable>
  );
}

export function NotificationsScreen({}: Props) {
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ['notifications'], queryFn: () => notificationsApi.list({page_size: 50, user_id: 'me'})});

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({queryKey: ['notifications']}),
  });

  const notifications = query.data?.notifications ?? [];
  const needsYou = notifications.filter((n) => NEEDS_YOU_TYPES.has(n.type) && !n.is_read);
  const earlier = notifications.filter((n) => !needsYou.includes(n));

  const markAllRead = () => {
    notifications.filter((n) => !n.is_read).forEach((n) => markReadMutation.mutate(n.id));
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{needsYou.length > 0 ? `Needs you · ${needsYou.length}` : ''}</Text>
        <Pressable onPress={markAllRead}>
          <Text style={styles.markAllRead}>Mark all read</Text>
        </Pressable>
      </View>

      {query.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {query.isSuccess && notifications.length === 0 && <Text style={styles.stateText}>No notifications yet.</Text>}

      <ScrollView contentContainerStyle={{padding: spacing.lg, gap: spacing.md}}>
        {needsYou.length > 0 && (
          <View style={{gap: spacing.xs}}>
            {needsYou.map((n) => (
              <NotificationRow key={n.id} notification={n} onPress={() => markReadMutation.mutate(n.id)} />
            ))}
          </View>
        )}
        {earlier.length > 0 && (
          <View>
            <Text style={styles.sectionLabel}>Earlier</Text>
            <View>
              {earlier.map((n) => (
                <NotificationRow key={n.id} notification={n} dim onPress={() => !n.is_read && markReadMutation.mutate(n.id)} />
              ))}
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  header: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.lg, paddingTop: spacing.sm},
  headerTitle: {fontSize: 11, letterSpacing: 0.5, textTransform: 'uppercase', color: colors.textSecondary},
  markAllRead: {color: colors.accentOnDark, fontSize: 11.5},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl},
  sectionLabel: {fontSize: 11, letterSpacing: 1, textTransform: 'uppercase', color: '#5A5A66', marginBottom: spacing.sm},
  row: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: 13,
    borderRadius: radius.row,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.xs,
  },
  rowNeedsYou: {borderColor: '#3B3670'},
  dot: {width: 6, height: 6, borderRadius: 3, marginTop: 6},
  title: {color: colors.textPrimary, fontSize: 13, fontWeight: '600'},
  titleDim: {color: colors.textPrimary, fontSize: 13},
  meta: {color: colors.textSecondary, fontSize: 11.5, marginTop: 3},
  glyph: {fontSize: 16, color: colors.accentOnDark},
});

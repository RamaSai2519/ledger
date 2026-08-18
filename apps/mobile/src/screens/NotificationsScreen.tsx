import React from 'react';
import {FlatList, Pressable, StyleSheet, Text, View} from 'react-native';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '@/navigation/types';
import type {Notification} from '@/api/client';
import {notificationsApi} from '@/api/client';
import {colors, radius, spacing} from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'Notifications'>;

const TYPE_LABELS: Record<Notification['type'], string> = {
  budget_threshold: 'Budget alert',
  budget_exceeded: 'Budget exceeded',
  sms_suggestion: 'Transaction suggestion',
  digest: 'Spending digest',
  bill_due: 'Bill due',
};

function summarize(notification: Notification): string {
  const p = notification.payload;
  switch (notification.type) {
    case 'budget_threshold':
    case 'budget_exceeded':
      return `${p.scope ?? 'Budget'} — ${typeof p.percent === 'number' ? p.percent.toFixed(0) : p.percent}% used`;
    case 'digest':
      return `Spent ${p.total_spent ?? 0} so far${p.top_category ? ` — top: ${p.top_category}` : ''}`;
    case 'bill_due':
      return `${p.wallet_name ?? 'A bill'} due ${p.due_date ?? 'soon'}`;
    default:
      return 'New notification';
  }
}

function NotificationRow({notification, onPress}: {notification: Notification; onPress: () => void}) {
  return (
    <Pressable style={styles.row} onPress={onPress}>
      {!notification.is_read && <View style={styles.unreadDot} />}
      <View style={{flex: 1, marginLeft: notification.is_read ? spacing.md + 6 : spacing.sm}}>
        <Text style={notification.is_read ? styles.typeTextRead : styles.typeText}>
          {TYPE_LABELS[notification.type] ?? notification.type}
        </Text>
        <Text style={styles.summaryText}>{summarize(notification)}</Text>
        <Text style={styles.dateText}>{new Date(notification.created_at).toLocaleString()}</Text>
      </View>
    </Pressable>
  );
}

export function NotificationsScreen({}: Props) {
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ['notifications'], queryFn: () => notificationsApi.list({page_size: 50})});

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({queryKey: ['notifications']}),
  });

  const notifications = query.data?.notifications ?? [];

  return (
    <View style={styles.container}>
      {query.isLoading && <Text style={styles.stateText}>Loading…</Text>}
      {query.isSuccess && notifications.length === 0 && (
        <Text style={styles.stateText}>No notifications yet.</Text>
      )}
      <FlatList
        data={notifications}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{gap: spacing.xs, padding: spacing.lg}}
        renderItem={({item}) => (
          <NotificationRow notification={item} onPress={() => !item.is_read && markReadMutation.mutate(item.id)} />
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.background},
  stateText: {color: colors.textSecondary, textAlign: 'center', marginTop: spacing.xl},
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
  },
  unreadDot: {width: 8, height: 8, borderRadius: 4, backgroundColor: colors.accent, marginTop: 6, marginRight: spacing.sm},
  typeText: {color: colors.textPrimary, fontSize: 14, fontWeight: '700'},
  typeTextRead: {color: colors.textSecondary, fontSize: 14, fontWeight: '400'},
  summaryText: {color: colors.textPrimary, fontSize: 13, marginTop: 2},
  dateText: {color: colors.textSecondary, fontSize: 11, marginTop: 4},
});

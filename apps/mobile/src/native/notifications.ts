import {Platform} from 'react-native';
import notifee, {AndroidImportance, AndroidStyle, EventType, type Event as NotifeeEvent} from '@notifee/react-native';
import type {NavigationContainerRefWithCurrent} from '@react-navigation/native';
import type {RootStackParamList} from '@/navigation/types';
import {smsApi} from '@/api/client';
import {refreshAccessTokenHeadless} from '@/state/authStore';

// LED-21: design s21 ("Push notification, expanded — on the lock screen")
// specifies a fully actionable notification for sms_suggestion pushes —
// standard FCM notification payloads can't carry action buttons, so the
// backend now sends this type as a data-only push (shared/notify.py's
// `push_data_only`) and this module builds the notification entirely
// client-side via notifee.
const SMS_SUGGESTION_CHANNEL_ID = 'sms-suggestions';

export async function ensureNotificationChannels(): Promise<void> {
  if (Platform.OS !== 'android') return;
  await notifee.createChannel({
    id: SMS_SUGGESTION_CHANNEL_ID,
    name: 'Transaction suggestions',
    importance: AndroidImportance.HIGH,
  });
}

type SmsSuggestionPushData = {
  sms_id?: string;
  amount?: string;
  merchant?: string;
  direction?: string;
  category_name?: string;
  wallet_label?: string;
  can_confirm?: string;
};

function notificationIdFor(smsId: string): string {
  return `sms-suggestion-${smsId}`;
}

// Renders as closely to s21 as stock Android notification styles allow: a
// bold amount/merchant title, an "Add as an expense?" body, a BigText
// second line carrying the category/wallet guess (the mockup's chip row —
// not reproducible without a custom RemoteViews layout), and the three
// actions baked onto the notification itself.
export async function displaySmsSuggestionNotification(data: SmsSuggestionPushData): Promise<void> {
  if (Platform.OS !== 'android' || !data.sms_id) return;
  await ensureNotificationChannels();

  const amount = data.amount ? `₹${Math.round(Number(data.amount))}` : 'A transaction';
  const merchant = data.merchant || 'a merchant';
  const title = data.wallet_label ? `${amount} at ${merchant}, ${data.wallet_label}` : `${amount} at ${merchant}`;
  const verb = data.direction === 'credit' ? 'Add as income?' : 'Add as an expense?';
  const canConfirm = data.can_confirm === 'true';
  const guessLine = data.category_name
    ? `Best guess: ${data.category_name}${data.wallet_label ? ` · ${data.wallet_label}` : ''}`
    : undefined;

  await notifee.displayNotification({
    id: notificationIdFor(data.sms_id),
    title,
    body: verb,
    data: {smsId: data.sms_id, type: 'sms_suggestion'},
    android: {
      channelId: SMS_SUGGESTION_CHANNEL_ID,
      smallIcon: 'ic_launcher',
      style: guessLine ? {type: AndroidStyle.BIGTEXT, text: `${verb}\n${guessLine}`} : undefined,
      pressAction: {id: 'default', launchActivity: 'default'},
      actions: [
        ...(canConfirm ? [{title: 'Confirm', pressAction: {id: 'confirm'}}] : []),
        {title: 'Edit', pressAction: {id: 'edit', launchActivity: 'default'}},
        {title: 'Dismiss', pressAction: {id: 'dismiss'}},
      ],
    },
  });
}

// Confirm/Dismiss must work from a killed app, so this can't rely on the
// zustand store having been rehydrated — refreshAccessTokenHeadless reads
// the persisted session straight out of Keychain when the in-memory store
// is empty (a fresh headless JS context, per push notification).
async function actOnSmsSuggestion(actionId: 'confirm' | 'dismiss', smsId: string): Promise<void> {
  const token = await refreshAccessTokenHeadless();
  if (!token) return;
  try {
    if (actionId === 'confirm') {
      await smsApi.accept(smsId);
    } else {
      await smsApi.dismiss(smsId);
    }
  } catch {
    // Best-effort: the user can still act from the in-app Notifications
    // list/Home SMS card if this silently fails (e.g. offline, or the
    // suggestion needs a wallet/category pick first — see `can_confirm`).
  }
}

// Shared by both the background handler (registered in index.js, runs in
// the headless JS context for a backgrounded/killed app) and the
// foreground handler below — Confirm/Dismiss never need navigation, so
// this half is platform-context-agnostic.
export async function handleSmsSuggestionNotificationEvent(event: NotifeeEvent): Promise<void> {
  const {type, detail} = event;
  if (type !== EventType.ACTION_PRESS && type !== EventType.PRESS) return;

  const smsId = detail.notification?.data?.smsId as string | undefined;
  if (!smsId) return;

  const actionId = detail.pressAction?.id;
  if (actionId === 'confirm' || actionId === 'dismiss') {
    await actOnSmsSuggestion(actionId, smsId);
    await notifee.cancelNotification(notificationIdFor(smsId));
  }
}

// 'default' (tap the notification body) and 'edit' both launch the app
// (launchActivity: 'default' above) — this is what routes that launch to
// Home once the app is actually running, mirroring push.ts's
// navigateForNotification for the plain-FCM notification types.
function shouldNavigateToHome(event: NotifeeEvent): boolean {
  const {type, detail} = event;
  if (type === EventType.PRESS) return true;
  if (type === EventType.ACTION_PRESS) return detail.pressAction?.id === 'edit';
  return false;
}

export function setupNotifeeOpenHandlers(
  navigationRef: NavigationContainerRefWithCurrent<RootStackParamList>,
  onActioned?: () => void,
): () => void {
  const navigateHome = () => {
    if (navigationRef.isReady()) navigationRef.navigate('Home' as never);
  };

  const unsubscribeForeground = notifee.onForegroundEvent((event) => {
    handleSmsSuggestionNotificationEvent(event).then(onActioned).catch(() => {});
    if (shouldNavigateToHome(event)) navigateHome();
  });

  notifee
    .getInitialNotification()
    .then((initial) => {
      if (initial) navigateHome();
    })
    .catch(() => {});

  return unsubscribeForeground;
}

import {PermissionsAndroid, Platform} from 'react-native';
import {getApp} from '@react-native-firebase/app';
import {
  AuthorizationStatus,
  getInitialNotification,
  getMessaging,
  getToken,
  onMessage,
  onNotificationOpenedApp,
  onTokenRefresh,
  requestPermission,
  type FirebaseMessagingTypes,
} from '@react-native-firebase/messaging';
import type {NavigationContainerRefWithCurrent} from '@react-navigation/native';
import type {RootStackParamList} from '@/navigation/types';
import type {NotificationType} from '@/api/client';
import {fcmApi} from '@/api/client';

// Modular API (not the namespaced `messaging()` call) — the namespaced API
// is deprecated as of RNFirebase v21 and logs a runtime warning on every
// call, even though it still works on the old architecture this app runs
// on. See https://rnfirebase.io/migrating-to-v22.
const messaging = getMessaging(getApp());

// LED-15: maps the `data.type` string every push carries (see
// shared/notify.py's `notify_household`, which always sets
// `data={"type": notification_type}`) to the screen a tap should land on.
// Falls back to Notifications for any type not listed here.
const DEEP_LINK_ROUTE: Partial<Record<NotificationType, keyof RootStackParamList>> = {
  budget_threshold: 'BudgetsList',
  budget_exceeded: 'BudgetsList',
  recurring_reminder: 'RecurringRulesList',
  sms_suggestion: 'Home',
  bill_due: 'Home',
  digest: 'Home',
};

// Android 13+ (API 33) requires this as a runtime-requested permission
// before any notification (including FCM) can be shown; below API 33 it's
// granted automatically and this call is a no-op.
export async function requestNotificationPermission(): Promise<boolean> {
  if (Platform.OS !== 'android') return false;

  if (Platform.Version >= 33) {
    const result = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS);
    if (result !== PermissionsAndroid.RESULTS.GRANTED) return false;
  }

  const authStatus = await requestPermission(messaging);
  return authStatus === AuthorizationStatus.AUTHORIZED || authStatus === AuthorizationStatus.PROVISIONAL;
}

// Retrieves the current FCM token and registers it against the logged-in
// user via POST /users/fcm-token (shared/fcm.py reads tokens off
// user.fcm_tokens for every push send). Also re-registers on token refresh
// (e.g. app reinstall, token rotation) for as long as the listener lives.
export function registerForPushNotifications(): () => void {
  let unsubscribed = false;

  getToken(messaging)
    .then((token) => {
      if (!unsubscribed && token) fcmApi.registerToken(token).catch(() => {});
    })
    .catch(() => {});

  const unsubscribeRefresh = onTokenRefresh(messaging, (token) => {
    fcmApi.registerToken(token).catch(() => {});
  });

  return () => {
    unsubscribed = true;
    unsubscribeRefresh();
  };
}

function navigateForNotification(
  navigationRef: NavigationContainerRefWithCurrent<RootStackParamList>,
  message: FirebaseMessagingTypes.RemoteMessage,
) {
  const type = message.data?.type as NotificationType | undefined;
  const route = (type && DEEP_LINK_ROUTE[type]) ?? 'Notifications';
  if (!navigationRef.isReady()) return;
  navigationRef.navigate(route as never);
}

// Wires the two "app was in background/killed and the user tapped the
// push" entry points, plus a foreground listener. `onForegroundMessage` is
// how a push received while the app is already open reaches the "signature
// moment" sheet (design s22) promptly instead of only on the next poll —
// see RootNavigator, which uses it to invalidate the sms-suggestions /
// notifications queries HomeScreen and NotificationsScreen already read.
export function setupNotificationOpenHandlers(
  navigationRef: NavigationContainerRefWithCurrent<RootStackParamList>,
  onForegroundMessage?: (data: FirebaseMessagingTypes.RemoteMessage['data']) => void,
): () => void {
  const unsubscribeOnMessage = onMessage(messaging, async (message) => {
    console.log('[push] foreground message received', message.data);
    onForegroundMessage?.(message.data);
  });

  const unsubscribeOpenedApp = onNotificationOpenedApp(messaging, (message) => {
    navigateForNotification(navigationRef, message);
  });

  getInitialNotification(messaging)
    .then((message) => {
      if (message) navigateForNotification(navigationRef, message);
    })
    .catch(() => {});

  return () => {
    unsubscribeOnMessage();
    unsubscribeOpenedApp();
  };
}

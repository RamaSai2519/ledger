/**
 * @format
 */
// Must be the first import — react-native-gesture-handler (LED-10 swipe-to-
// archive) installs its native event handlers at module-init time.
import 'react-native-gesture-handler';
import {AppRegistry} from 'react-native';
import {getApp} from '@react-native-firebase/app';
import {getMessaging, setBackgroundMessageHandler} from '@react-native-firebase/messaging';
import notifee from '@notifee/react-native';
import App from './App';
import {name as appName} from './app.json';
import {displaySmsSuggestionNotification, handleSmsSuggestionNotificationEvent} from './src/native/notifications';

// LED-15: must be registered outside of any React component (module scope,
// before AppRegistry.registerComponent) — this is what lets it run in the
// headless JS context Android spins up for a push received while the app is
// backgrounded or fully killed. The RootNavigator notification-open
// handlers (src/native/push.ts) cover the "user tapped the push" case for
// the plain-FCM notification types; sms_suggestion (LED-21) is sent
// data-only precisely so it lands here instead, where notifee builds the
// actionable notification design s21 specifies. Modular API — see
// src/native/push.ts for why.
setBackgroundMessageHandler(getMessaging(getApp()), async (message) => {
  console.log('[push] background message received', message.data);
  if (message.data?.type === 'sms_suggestion') {
    await displaySmsSuggestionNotification(message.data);
  }
});

// Confirm/Dismiss action presses on the sms_suggestion notification — also
// headless, also module scope. Tap (default) / Edit instead launch the app
// (launchActivity: 'default' in notifee.displayNotification) and are
// handled once running, by setupNotifeeOpenHandlers in RootNavigator.
notifee.onBackgroundEvent(async (event) => {
  await handleSmsSuggestionNotificationEvent(event);
});

AppRegistry.registerComponent(appName, () => App);

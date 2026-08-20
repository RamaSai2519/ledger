/**
 * @format
 */
// Must be the first import — react-native-gesture-handler (LED-10 swipe-to-
// archive) installs its native event handlers at module-init time.
import 'react-native-gesture-handler';
import {AppRegistry} from 'react-native';
import {getApp} from '@react-native-firebase/app';
import {getMessaging, setBackgroundMessageHandler} from '@react-native-firebase/messaging';
import App from './App';
import {name as appName} from './app.json';

// LED-15: must be registered outside of any React component (module scope,
// before AppRegistry.registerComponent) — this is what lets it run in the
// headless JS context Android spins up for a push received while the app is
// backgrounded or fully killed. Just logs for this pass; the RootNavigator
// notification-open handlers (src/native/push.ts) cover the "user tapped
// the push" case. Modular API — see src/native/push.ts for why.
setBackgroundMessageHandler(getMessaging(getApp()), async (message) => {
  console.log('[push] background message received', message.data);
});

AppRegistry.registerComponent(appName, () => App);

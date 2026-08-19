/**
 * @format
 */
// Must be the first import — react-native-gesture-handler (LED-10 swipe-to-
// archive) installs its native event handlers at module-init time.
import 'react-native-gesture-handler';
import {AppRegistry} from 'react-native';
import App from './App';
import {name as appName} from './app.json';

AppRegistry.registerComponent(appName, () => App);

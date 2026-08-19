import {Platform} from 'react-native';
import ReactNativeBiometrics from 'react-native-biometrics';

const rnBiometrics = new ReactNativeBiometrics();

export async function isBiometricSensorAvailable(): Promise<boolean> {
  if (Platform.OS !== 'android') return false;
  try {
    const {available} = await rnBiometrics.isSensorAvailable();
    return available;
  } catch {
    return false;
  }
}

export async function promptBiometricUnlock(promptMessage = 'Unlock Ledger'): Promise<boolean> {
  try {
    const {success} = await rnBiometrics.simplePrompt({promptMessage});
    return success;
  } catch {
    return false;
  }
}

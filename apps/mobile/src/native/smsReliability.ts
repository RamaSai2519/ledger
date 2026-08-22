import {NativeModules, Platform} from 'react-native';

const {SmsReliabilityModule} = NativeModules as {
  SmsReliabilityModule?: {
    isIgnoringBatteryOptimizations(): Promise<boolean>;
    requestIgnoreBatteryOptimizations(): void;
  };
};

// LED-31: whether Ledger is exempt from Doze/App Standby battery
// optimization — the OS otherwise defers the WorkManager job that
// forwards an already-received SMS for an indeterminate amount of time.
export async function isIgnoringBatteryOptimizations(): Promise<boolean> {
  if (Platform.OS !== 'android' || !SmsReliabilityModule) return false;
  try {
    return await SmsReliabilityModule.isIgnoringBatteryOptimizations();
  } catch {
    return false;
  }
}

// Opens the system "ignore battery optimizations" dialog for this app.
// There's no way to grant this from code — it always requires the user's
// explicit tap on the system dialog.
export function requestIgnoreBatteryOptimizations(): void {
  if (Platform.OS !== 'android' || !SmsReliabilityModule) return;
  SmsReliabilityModule.requestIgnoreBatteryOptimizations();
}

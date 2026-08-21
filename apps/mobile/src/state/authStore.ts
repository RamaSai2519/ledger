import AsyncStorage from '@react-native-async-storage/async-storage';
import {NativeModules, Platform} from 'react-native';
import * as Keychain from 'react-native-keychain';
import {create} from 'zustand';
import {authApi} from '@/api/client';

// Not a secret — just a UI preference, so plain AsyncStorage (not Keychain)
// is fine here.
const BIOMETRIC_ENABLED_KEY = 'biometric_unlock_enabled';

// LED-7: hands the refresh token to the native SmsIngestWorker (Android
// only), which runs via WorkManager and may execute after the JS runtime
// has been killed — it can't read zustand state or secure storage directly.
// See android/app/.../sms/AuthTokenModule.kt.
const AuthTokenModule = Platform.OS === 'android' ? NativeModules.AuthTokenModule : null;

// LED-9: session snapshot persisted via react-native-keychain (Android
// Keystore-backed EncryptedSharedPreferences / iOS Keychain), replacing the
// plaintext AsyncStorage the original Phase-1 scaffold used. A single
// generic-password entry under this service holds everything needed to
// restore a session on cold start — /auth/refresh only returns a new
// access_token, not the user/household context, so that context has to be
// persisted alongside the refresh token.
const SESSION_SERVICE = 'com.ledgerapp.mobile.session';

type PersistedSession = {
  userId: string;
  name: string;
  householdId: string | null;
  householdName: string | null;
  refreshToken: string;
  pinHash: string | null;
};

function persistSession(snapshot: PersistedSession) {
  Keychain.setGenericPassword('ledger', JSON.stringify(snapshot), {service: SESSION_SERVICE}).catch(() => {});
}

async function readPersistedSession(): Promise<PersistedSession | null> {
  try {
    const result = await Keychain.getGenericPassword({service: SESSION_SERVICE});
    if (!result) return null;
    return JSON.parse(result.password) as PersistedSession;
  } catch {
    return null;
  }
}

function clearPersistedSession() {
  Keychain.resetGenericPassword({service: SESSION_SERVICE}).catch(() => {});
}

// Not a real cryptographic hash — just a fast local-comparison hash so the
// PIN itself is never round-tripped in plaintext through the store/keychain.
// Good enough for local app-lock gating, not a security boundary on its own
// (the security boundary is the access/refresh token pair, now stored
// encrypted — see SESSION_SERVICE above).
function hashPin(pin: string): string {
  let hash = 5381;
  for (let i = 0; i < pin.length; i++) {
    hash = (hash * 33) ^ pin.charCodeAt(i);
  }
  return (hash >>> 0).toString(16);
}

type AuthState = {
  userId: string | null;
  name: string | null;
  householdId: string | null;
  householdName: string | null;
  accessToken: string | null;
  refreshToken: string | null;
  pinHash: string | null;
  // Whether the one-time cold-start rehydrate attempt (from persisted
  // Keychain state, via /auth/refresh) has finished — SplashScreen waits on
  // this before deciding where to route, instead of the old snapshot-in-
  // memory-only check that always looked logged-out after a process restart.
  hydrated: boolean;
  hydrate: () => Promise<void>;
  biometricEnabled: boolean;
  setBiometricEnabled: (enabled: boolean) => void;
  setSession: (session: {
    userId: string;
    name: string;
    householdId: string | null;
    accessToken: string;
    refreshToken: string;
  }) => void;
  setHouseholdId: (householdId: string, householdName?: string) => void;
  setPin: (pin: string) => void;
  verifyPin: (pin: string) => boolean;
  clearSession: () => void;
};

export const useAuthStore = create<AuthState>((set, get) => ({
  userId: null,
  name: null,
  householdId: null,
  householdName: null,
  accessToken: null,
  refreshToken: null,
  pinHash: null,
  hydrated: false,
  biometricEnabled: false,
  setBiometricEnabled: (enabled) => {
    set({biometricEnabled: enabled});
    AsyncStorage.setItem(BIOMETRIC_ENABLED_KEY, enabled ? '1' : '0').catch(() => {});
  },
  hydrate: async () => {
    if (get().hydrated) return;
    AsyncStorage.getItem(BIOMETRIC_ENABLED_KEY)
      .then((value) => set({biometricEnabled: value === '1'}))
      .catch(() => {});
    const snapshot = await readPersistedSession();
    if (!snapshot) {
      set({hydrated: true});
      return;
    }
    // /auth/refresh reads the refresh token from the store (auth: 'refresh'),
    // so it needs to be in state before the call is made.
    set({refreshToken: snapshot.refreshToken});
    try {
      const {access_token} = await authApi.refresh();
      set({
        userId: snapshot.userId,
        name: snapshot.name,
        householdId: snapshot.householdId,
        householdName: snapshot.householdName,
        pinHash: snapshot.pinHash,
        accessToken: access_token,
        hydrated: true,
      });
      AuthTokenModule?.setRefreshToken(snapshot.refreshToken);
    } catch {
      // Refresh token expired/revoked (e.g. logged out from the other
      // partner's device) — fall back to a clean logged-out state.
      set({userId: null, name: null, householdId: null, householdName: null, accessToken: null, refreshToken: null, pinHash: null, hydrated: true});
      clearPersistedSession();
      AuthTokenModule?.clearRefreshToken();
    }
  },
  setSession: (session) => {
    set({
      userId: session.userId,
      name: session.name,
      householdId: session.householdId,
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
    });
    persistSession({
      userId: session.userId,
      name: session.name,
      householdId: session.householdId,
      householdName: get().householdName,
      refreshToken: session.refreshToken,
      pinHash: get().pinHash,
    });
    AuthTokenModule?.setRefreshToken(session.refreshToken);
  },
  setHouseholdId: (householdId, householdName) => {
    const resolvedName = householdName ?? get().householdName;
    set({householdId, householdName: resolvedName});
    const {userId, name, refreshToken, pinHash} = get();
    if (refreshToken) {
      persistSession({userId: userId!, name: name!, householdId, householdName: resolvedName, refreshToken, pinHash});
    }
  },
  setPin: (pin) => {
    const pinHash = hashPin(pin);
    set({pinHash});
    const {userId, name, householdId, householdName, refreshToken} = get();
    if (refreshToken) {
      persistSession({userId: userId!, name: name!, householdId, householdName, refreshToken, pinHash});
    }
  },
  verifyPin: (pin) => get().pinHash === hashPin(pin),
  clearSession: () => {
    set({userId: null, name: null, householdId: null, householdName: null, accessToken: null, refreshToken: null, pinHash: null});
    clearPersistedSession();
    AuthTokenModule?.clearRefreshToken();
  },
}));

// LED-21: a notifee background-event handler (headless JS, e.g. a
// Confirm/Dismiss tap on a killed app's SMS-suggestion notification) runs
// in a fresh JS context where this store's in-memory state is never
// hydrated — `hydrate()` isn't called there, only from a mounted
// SplashScreen. This mirrors `hydrate`'s own refresh-token-from-Keychain
// flow but returns the access token directly instead of routing through
// component state, and is a no-op read (not a full session restore) when
// the store already has a live access token, i.e. the app is actually
// running in the foreground.
export async function refreshAccessTokenHeadless(): Promise<string | null> {
  const existing = useAuthStore.getState().accessToken;
  if (existing) return existing;

  const snapshot = await readPersistedSession();
  if (!snapshot?.refreshToken) return null;

  useAuthStore.setState({refreshToken: snapshot.refreshToken});
  try {
    const {access_token} = await authApi.refresh();
    useAuthStore.setState({accessToken: access_token});
    return access_token;
  } catch {
    return null;
  }
}

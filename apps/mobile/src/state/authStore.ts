import AsyncStorage from '@react-native-async-storage/async-storage';
import {create} from 'zustand';

// Not a real cryptographic hash — just enough to avoid keeping the PIN as
// plaintext in memory/AsyncStorage while there's no native secure-storage
// library wired up yet (same "not production-safe, Phase-1-native
// follow-up" caveat as the refresh token below). Good enough for local
// app-lock gating, not a security boundary on its own.
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

// AsyncStorage, not react-native-mmkv/expo-secure-store — no encrypted
// storage lib is wired up yet (deferred with the rest of the native/biometric
// work, see docs/decisions/0004). Do not treat this as production-safe token
// storage; the plaintext-vs-encrypted swap is Phase-1-native follow-up work.
export const useAuthStore = create<AuthState>((set, get) => ({
  userId: null,
  name: null,
  householdId: null,
  householdName: null,
  accessToken: null,
  refreshToken: null,
  pinHash: null,
  setSession: (session) => {
    set({
      userId: session.userId,
      name: session.name,
      householdId: session.householdId,
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
    });
    AsyncStorage.setItem('refresh_token', session.refreshToken).catch(() => {});
  },
  setHouseholdId: (householdId, householdName) => set({householdId, householdName: householdName ?? get().householdName}),
  setPin: (pin) => set({pinHash: hashPin(pin)}),
  verifyPin: (pin) => get().pinHash === hashPin(pin),
  clearSession: () => {
    set({userId: null, name: null, householdId: null, householdName: null, accessToken: null, refreshToken: null, pinHash: null});
    AsyncStorage.removeItem('refresh_token').catch(() => {});
  },
}));

import AsyncStorage from '@react-native-async-storage/async-storage';
import {create} from 'zustand';

type AuthState = {
  userId: string | null;
  name: string | null;
  householdId: string | null;
  accessToken: string | null;
  refreshToken: string | null;
  setSession: (session: {
    userId: string;
    name: string;
    householdId: string | null;
    accessToken: string;
    refreshToken: string;
  }) => void;
  setHouseholdId: (householdId: string) => void;
  clearSession: () => void;
};

// AsyncStorage, not react-native-mmkv/expo-secure-store — no encrypted
// storage lib is wired up yet (deferred with the rest of the native/biometric
// work, see docs/decisions/0004). Do not treat this as production-safe token
// storage; the plaintext-vs-encrypted swap is Phase-1-native follow-up work.
export const useAuthStore = create<AuthState>((set) => ({
  userId: null,
  name: null,
  householdId: null,
  accessToken: null,
  refreshToken: null,
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
  setHouseholdId: (householdId) => set({householdId}),
  clearSession: () => {
    set({userId: null, name: null, householdId: null, accessToken: null, refreshToken: null});
    AsyncStorage.removeItem('refresh_token').catch(() => {});
  },
}));

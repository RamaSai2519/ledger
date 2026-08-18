# apps/mobile

React Native (bare) app. Navigation shell (Splash → Sign Up/Log In →
Household Create-or-Join → Home stub) wired to the Phase 1 backend
endpoints (`src/api/client.ts`), TanStack Query for server state, Zustand
for local session state (`src/state/authStore.ts`), dark theme tokens from
`DESIGN_BRIEF.md` §4 (`src/theme/tokens.ts`).

## Known gaps (deferred, see docs/decisions/0004)

- **No `android/`/`ios/` native project directories yet.** `npx react-native
  init` needs interactive/network access this scaffold's build environment
  didn't reliably have; generate them with `npx react-native@latest init
  --skip-install` (or `npx @react-native-community/cli init`) into a scratch
  dir and copy the native folders in, or run it directly in this directory
  once you have a working RN CLI locally. Until then, this is a JS/TS-only
  scaffold — verify with `npm install && npm run typecheck`, not a device
  build.
- No native Kotlin SMS `BroadcastReceiver` module (Phase 5).
- No biometric/encrypted-storage wiring — `authStore` persists the refresh
  token via plain `AsyncStorage`, not `react-native-mmkv`/`expo-secure-store`.
- `API_BASE_URL` in `src/api/client.ts` is empty — set it to the deployed
  API Gateway URL (`terraform output api_url` in `infra/terraform/`).

## Development

```bash
npm install
npm run typecheck
```

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

## Play Console internal testing releases

Published from a local machine via [Gradle Play
Publisher](https://github.com/Triplet/gradle-play-publisher) (the `play {}`
block in `android/app/build.gradle`, pinned to the 3.x line since 4.x needs
Gradle 9.1+ and this project is on 8.8) — no CI involved, so `versionCode`
(raw `git rev-list --count HEAD`, `android/app/build.gradle`) is always
computed from a full local checkout rather than risking a shallow CI
clone under-counting it and getting rejected as "version code too low or
has already been used."

### One-time setup (must be done by a human in Google's web UI — nothing
### here can be scripted from this repo)

Google's Play Developer API can't create a brand-new app's store listing,
content rating, or data safety form — the app must already have at least
one manual release in Play Console before API-based uploads to any track
work. Once that's true:

1. **Create the service account** (Google Cloud Console, same project as
   Firebase or a fresh one): IAM & Admin → Service Accounts → Create, then
   Keys → Add key → JSON. Keep the downloaded file private — never commit
   it (see `.gitignore`); save it at `android/app/play-service-account.json`
   (this task's default credentials path).
2. **Grant it Play Console access**: Play Console → Setup → API access →
   link the Cloud project → find the service account → Grant access, with
   at least *Release to testing tracks* permission for this app.
3. **Enable the Play Developer API** for that Cloud project (Google Cloud
   Console → APIs & Services → Library → "Google Play Android Developer
   API" → Enable) — a fresh project has it disabled by default and the
   first publish attempt fails with a `SERVICE_DISABLED` 403 otherwise.
4. **Generate a release keystore**, if one doesn't already exist locally:
   `keytool -genkeypair -storetype PKCS12 -keystore app/release.keystore
   -alias ledger -keyalg RSA -keysize 2048 -validity 10000` from
   `android/`, and a matching `android/keystore.properties` (see the
   `keystoreProperties` block in `android/app/build.gradle` for the
   expected keys). **Reuse the existing keystore for every release after
   the first** — Play Console permanently rejects uploads signed with a
   different key than the app's original upload (unless Play App Signing's
   formal key-rotation flow is used instead of just swapping the file).

### Running it

```bash
cd android
./gradlew publishReleaseBundle
```

`versionCode`/`versionName` (`1.2.<commit count>`) are derived
automatically from the current commit, so every run is a distinct,
strictly-increasing upload — nothing to bump by hand except the `1.2.`
major/minor prefix itself, for a real milestone.

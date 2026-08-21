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

`.github/workflows/deploy-mobile.yml` (`workflow_dispatch` only — an
internal-testing upload is a real release to every tester on the list, not
something that should fire on every merge) builds the signed release AAB
and publishes it to Play Console's internal track via [Gradle Play
Publisher](https://github.com/Triplet/gradle-play-publisher) (the `play {}`
block in `android/app/build.gradle`).

### One-time setup (must be done by a human in Google's/GitHub's web UI —
### nothing here can be scripted from this repo)

Google's Play Developer API can't create a brand-new app's store listing,
content rating, or data safety form — the app must already have at least
one manual release in Play Console before API-based uploads to any track
work. Once that's true:

1. **Create the service account** (Google Cloud Console, same project as
   Firebase or a fresh one): IAM & Admin → Service Accounts → Create, then
   Keys → Add key → JSON. Keep the downloaded file private — never commit
   it (see `.gitignore`).
2. **Grant it Play Console access**: Play Console → Setup → API access →
   link the Cloud project → find the service account → Grant access, with
   at least *Release to testing tracks* permission for this app.
3. **Generate a release keystore**, if one doesn't already exist locally:
   `keytool -genkeypair -storetype PKCS12 -keystore app/release.keystore
   -alias ledger -keyalg RSA -keysize 2048 -validity 10000` from
   `android/`.
4. **Add the GitHub Actions secrets** (repo Settings → Secrets and
   variables → Actions) — do this yourself via the GitHub web UI or `gh
   secret set <NAME> < path/to/file`, never by pasting key material into a
   chat/assistant session:
   - `ANDROID_KEYSTORE_BASE64` — `base64 -w0 app/release.keystore`
   - `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`
   - `PLAY_SERVICE_ACCOUNT_JSON` — the full contents of the service-account
     JSON key from step 1

### Running it

GitHub → Actions → "Deploy mobile (Play Console internal testing)" → Run
workflow. `versionCode` (raw git commit count) and `versionName`
(`1.2.<commit count>`, `android/app/build.gradle`) are derived
automatically, so every run is a distinct, strictly-increasing upload —
nothing to bump by hand except the `1.2.` major/minor prefix itself, for a
real milestone.

To run the same publish locally instead: drop the service-account JSON at
`android/play-service-account.json` (gitignored) and `keystore.properties`
per `android/app/build.gradle`'s existing local-signing setup, then
`./gradlew publishReleaseBundle` from `android/`.

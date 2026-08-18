# ADR 0004: React Native (bare) for mobile; native SMS module deferred

**Status:** Accepted

## Context

`IMPLEMENTATION_PLAN.md` §3/§13 specifies React Native bare workflow (not
Expo-managed) because the SMS auto-detection feature (§7) needs a custom
native Kotlin `BroadcastReceiver` module that keeps working when the app is
backgrounded/killed — not achievable in a managed Expo project without
ejecting anyway.

## Decision

`apps/mobile` is scaffolded as a bare React Native project now (navigation
shell, TanStack Query + Zustand, dark theme tokens from the Claude Design
project). The native Kotlin SMS module, the Android permission-rationale
flow, and Firebase push wiring are **deferred** to the Phase 5 SMS-pipeline
work (tracked separately in Jira) — this session only scopes through Phase 1
(auth & household).

## Consequences

- The scaffolded app has no working SMS detection yet — manual transaction
  entry (Phase 2, also deferred) will be the only way to log a transaction
  once that phase lands.
- No Android SDK/emulator was available in the environment this scaffold
  was built in, so the mobile app has only been verified at the
  `npm install` / TypeScript-compile level, not run on a device or emulator.

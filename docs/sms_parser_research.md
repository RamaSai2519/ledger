# SMS parser prior-art research (LED-18)

Brief survey done before implementing the layered parser in
`services/api/src/shared/sms/`, per the spec's requirement to check for
reusable open-source work before writing bank-SMS regex from scratch.

## What was found

| Repo | License | Approach | Notes |
|---|---|---|---|
| [saurabhgupta050890/transaction-sms-parser](https://github.com/saurabhgupta050890/transaction-sms-parser) | MIT | JVM/Kotlin, per-bank regex + keyword rules | Closest in spirit to this project's data-driven-rules approach; JVM-only, not directly importable into a Python backend. |
| [MabudAlam/transaction_sms_parser](https://github.com/MabudAlam/transaction_sms_parser) | MIT | Dart/Flutter, 30+ Indian banks | Dart, not applicable to either this repo's Python backend or its React Native (JS) mobile app without a full rewrite. |
| [sarim2000/pennywiseai-tracker (PennyWise)](https://github.com/sarim2000/pennywiseai-tracker) | AGPL v3 | Flutter app, 50+ banks/100+ UPI handles, on-device parsing | **AGPL v3 is copyleft and explicitly excluded** by CLAUDE.md's "no incompatible GPL/copyleft code" constraint - not usable even if the language matched. |
| [MalayPalace/Bank-Statement-Utility](https://github.com/MalayPalace/Bank-Statement-Utility) | unspecified | Bank *statement file* parsing (CSV/PDF), not SMS | Different problem (post-hoc statement import, not live SMS), not applicable here. |

## Decision: nothing reused, written from scratch

- No candidate is both **license-compatible** (MIT/permissive, not
  AGPL/GPL) **and** in a language this stack can import directly (Python
  for the backend parser). The one MIT/permissive option close in spirit
  (`transaction-sms-parser`) is JVM/Kotlin; porting its *ideas* (regex
  structure, per-bank keyword tables) rather than its code was the
  practical path, and that's effectively what
  `shared/sms_parser_rules_seed.py` + `shared/sms/` already do independently.
- Bank SMS formats are short-lived, regionally specific, and change without
  notice (the whole reason CLAUDE.md mandates data-driven rules over a
  static library) - a vendored dependency wouldn't reduce ongoing
  maintenance burden even if the license/language lined up.
- No code, regex patterns, or data tables from any of the above were copied
  into this repo. `shared/sms/*.py` and `shared/sms_parser_rules_seed.py`
  are original, written against real (synthetic, for tests) and
  sanitized-real (via `scripts/sms_dev/`) SMS samples.

## If this changes later

If a permissively-licensed (MIT/BSD/Apache-2.0), Python-importable parser
library appears, re-evaluate before extending `shared/sms/` further by
hand - but keep the actual per-bank *patterns* in the `sms_parser_rules`
Mongo collection regardless (CLAUDE.md's non-negotiable constraint doesn't
change based on tooling).

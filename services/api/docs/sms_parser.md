# SMS transaction parser (LED-18)

Architecture, how to extend it, and how to run the dev-only ADB validation
pipeline. See also `plan.md` §7 (product-level pipeline) and `CLAUDE.md`'s
non-negotiable constraints (data-driven rules, data minimization).

## Architecture

```
SMS
 -> SmsNormalizer                 (shared/sms/normalizer.py)
 -> TransactionClassifier         (shared/sms/classifier.py)
 -> InstitutionResolver           (shared/sms/institution_resolver.py, sender_resolver.py)
 -> TransactionTypeDetector       (shared/sms/type_detector.py)
 -> extractors/*                  (amount, merchant+counterparty+payment_method,
                                    account, transaction_id, date, balance)
 -> MerchantNormalizer            (shared/sms/merchant_normalizer.py)
 -> TransactionValidator          (shared/sms/validator.py)
 -> ConfidenceScorer              (shared/sms/confidence.py)
 -> TransactionDeduplicator       (shared/sms/deduplicator.py, called from shared/sms_parsing.py)
 -> ParsedTransaction             (shared/sms/types.py)
```

`shared/sms/pipeline.py`'s `SmsParserPipeline` wires all of the above in
order. `shared/sms_parsing.py` is the compatibility layer
`models/sms_ingest/compute.py` actually calls - it flattens
`ParsedTransaction` into the dict shape that existed before LED-18 (plus new
keys), and owns the DB-touching parts (loading `sms_parser_rules`/
`merchant_aliases`, wallet/dedup lookups) that the pure `shared/sms/`
package deliberately doesn't know about.

Every layer is a small, independently unit-testable class/function with no
Mongo/Flask dependency - see `tests/test_sms_parsing_pipeline.py`, which
drives `SmsParserPipeline` directly against
`tests/fixtures/synthetic_sms_corpus.py`.

### Data-driven parts (CLAUDE.md's non-negotiable constraint)

- **`sms_parser_rules`** (Mongo, seeded by `shared/sms_parser_rules_seed.py`):
  per-bank `sender_ids`, `institution_name`/`aliases`/`keywords`
  (institution-resolution evidence), and the legacy `patterns` field (kept
  for `POST /sms/parser-rules` household-custom-rule compatibility, but no
  longer executed by the pipeline itself - see "Known limitations" below).
- **`merchant_aliases`** (Mongo, seeded by `shared/merchant_aliases_seed.py`):
  raw merchant string variants -> canonical display name, used by
  `MerchantNormalizer`.

### How to add a new bank

1. Add an entry to `_BANKS` in `shared/sms_parser_rules_seed.py`:
   `bank_code`, `sender_ids` (all known DLT-prefixed variants),
   `institution_name`, `aliases`, `keywords`.
2. Run `pipenv run python -m scripts.seed_sms_parser_rules` (or let the
   next deploy's seed step run it - it's idempotent, upserted by
   `bank_code`).
3. That's it for institution *resolution*. The actual field extraction
   (amount/merchant/date/etc.) is bank-agnostic - `shared/sms/extractors/*`
   handle format variance generically (currency spelling, Indian digit
   grouping, masked-account spellings, date formats) rather than needing a
   bank-specific regex. If a specific bank's wording genuinely isn't
   covered by an extractor (e.g. a new debit verb your bank uses that isn't
   in `normalizer.py`'s synonym list), add the missing synonym there -
   check `normalizer.py`, `classifier.py`'s `_TXN_VERB_RE`, and
   `extractors/amount.py`'s `_TRANSACTION_KEYWORDS` together, since all
   three need to agree on what counts as a transaction verb.
4. Add a case to `tests/fixtures/synthetic_sms_corpus.py` and rerun
   `pipenv run pytest tests/test_sms_parsing_pipeline.py -v`.

### Known limitations

- Household-custom `sms_parser_rules.patterns` (created via
  `POST /sms/parser-rules`) are stored and listable but **not executed** by
  the new pipeline - the old approach (one fixed regex per bank) has been
  replaced by generic, bank-agnostic extractors. Custom rules still
  contribute `sender_ids` to `InstitutionResolver`. If a household truly
  needs bank-specific *extraction* behavior beyond what the generic
  extractors handle, that's a gap to close in a follow-up, not something
  this pass attempted.
- `MerchantExtractor`'s merchant-vs-counterparty (person) heuristic is
  shape-based (ALL-CAPS/business-suffix vs Title-Case-two-word) when no
  `merchant_aliases` entry exists - real bank SMS often prints person names
  in ALL CAPS too, which reads as "merchant" by this heuristic. Known
  false-negative on the counterparty side; not a data-minimization risk
  (nothing is redacted or dropped, just filed under the wrong field).
- The dev-pipeline's sanitizer redacts a counterparty name to a
  placeholder like `PERSON1234` before the corpus is re-parsed for
  evaluation - that placeholder's shape (a single ALL-CAPS-ish token) can
  itself look like a merchant to `MerchantExtractor`, occasionally flipping
  a counterparty into an apparent merchant *in the sanitized corpus only*
  (never in production, where the pipeline runs on real, unredacted SMS
  once). Worth knowing when reading `sms-evaluate` output.
- `AmountExtractor`'s context window is deliberately asymmetric (large
  window before an amount, short window after) since bank SMS almost
  always puts a label before the value it describes ("Avl Bal Rs.X",
  "Available limit INR Y") - an amount whose qualifying label appears more
  than ~20 characters *after* it won't be picked up.

## Dev-only ADB validation pipeline

```
Phone --ADB--> Debug Android SMS exporter --> JSON on dev machine
                                                    |
                                                    v
                                              sanitizer.py
                                                    |
                                                    v
                                        real-world local corpus
                                          /          |          \
                                     parser      evaluation   regression tests
```

Commands (Pipfile `[scripts]` aliases - this repo's `npm run x` equivalent,
since `services/api` is Python, not Node):

```bash
cd services/api/src
pipenv run sms-pull            # pull SMS from the connected device
pipenv run sms-sanitize        # sanitize the latest raw pull
pipenv run sms-validate        # pull+sanitize+parse+report in one go (--pull to force a fresh pull first)
pipenv run sms-review          # interactive correct/incorrect/edit/skip over low-confidence results
pipenv run sms-promote-test    # turn reviewed-correct examples into permanent regression fixtures
pipenv run sms-evaluate        # precision/recall/field-accuracy/false-positive-rate against reviewed corrections
```

All of this reads/writes `services/api/.sms_dev_data/` (git-ignored). Raw,
unsanitized SMS text only ever lives in `.sms_dev_data/raw/` and is never
printed to the terminal or written anywhere else - every other command
(`report.py`, `cli.py`) only ever touches `sanitized_text`.

### Retrieval paths

1. **`adb shell content query`** (`scripts/sms_dev/adb_client.py:pull_sms_content_query`)
   - fast, no app install needed, but returns empty/restricted on many OEM
     ROMs (MIUI, One UI, etc. commonly block shell-level SMS provider reads).
2. **Debug-only Android exporter** (`pull_sms_debug_helper`) - triggers
   `apps/mobile/android/app/src/debug/.../SmsExportReceiver.kt` via
   `adb shell am broadcast`, then `adb pull`s its JSON output. Requires a
   **debug build** of the app installed on the device (the receiver and its
   `READ_SMS` permission only exist in `src/debug/AndroidManifest.xml` -
   never merged into a release build).

`pull_sms()` tries (1) first, falls through to (2) automatically if (1)
comes back empty.

### Rerunning the full pipeline end to end

```bash
cd services/api/src
pipenv install
pipenv run sms-validate --pull   # connect your phone first, USB debugging enabled
pipenv run sms-review            # go through the low-confidence cases it flags
pipenv run sms-promote-test      # lock in the ones you confirmed as correct
pipenv run pytest tests/test_sms_real_world_regression.py -v
pipenv run sms-evaluate
```

### Privacy

- The sanitizer (`scripts/sms_dev/sanitizer.py`) redacts account/card
  numbers, UPI IDs, phone numbers, transaction IDs/UTRs, emails, and
  counterparty names before anything is re-parsed, printed, or written to a
  report - see `tests/test_sms_dev_sanitizer.py`.
- Redaction is deterministic (stable hash-derived replacement values, not
  random) so reruns produce a stable diff.
- Promoted regression fixtures (`tests/fixtures/real_world_promoted/*.json`)
  are the *only* artifact from this pipeline that's git-tracked - review
  what you promote before committing it.

"""Dev-only ADB SMS validation pipeline CLI (spec Parts 16-21).

    PHONE -> ADB -> raw local SMS dataset -> sanitizer -> anonymized test
    corpus -> parser -> evaluation report

Entry points registered as Pipfile `[scripts]` aliases (this repo's actual
`npm run x` equivalent - see services/api/src/Pipfile):

    pipenv run sms-pull           pull SMS from the connected device
    pipenv run sms-sanitize       sanitize the latest raw pull
    pipenv run sms-validate       pull -> sanitize -> parse -> print report
    pipenv run sms-review         interactive human review of low-confidence cases
    pipenv run sms-promote-test   turn a reviewed-correct example into a regression test fixture
    pipenv run sms-evaluate       precision/recall/accuracy metrics against reviewed corrections

Everything this CLI writes to disk lives under services/api/.sms_dev_data/,
which is git-ignored - see the root .gitignore. Raw (unsanitized) SMS never
leaves that directory and is never printed to the terminal by any command
other than `pull` writing it to disk.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from scripts.sms_dev import adb_client, report as report_mod
from scripts.sms_dev.sanitizer import sanitize

_DATA_DIR = Path(__file__).resolve().parents[3] / ".sms_dev_data"
_RAW_DIR = _DATA_DIR / "raw"
_SANITIZED_DIR = _DATA_DIR / "sanitized"
_REPORTS_DIR = _DATA_DIR / "reports"
_CORRECTIONS_DIR = _DATA_DIR / "corrections"
_PROMOTED_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "real_world_promoted"

_TRANSACTIONAL_SENDER_HINT = None  # placeholder for a future allow-list-aware pre-filter, kept out of MVP scope


def _ensure_dirs() -> None:
    for d in (_RAW_DIR, _SANITIZED_DIR, _REPORTS_DIR, _CORRECTIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _latest_file(directory: Path, pattern: str) -> Path | None:
    files = sorted(directory.glob(pattern))
    return files[-1] if files else None


def _normalize_pulled_row(row: dict) -> dict | None:
    """`content_query` rows use `address`/`body`/`_id`; the debug-helper's
    JSON uses `id`/`address`/`body` too but with `date_millis` instead of
    `date` - normalize both into one shape."""
    address = row.get("address")
    body = row.get("body")
    if not address or not body:
        return None
    return {
        "id": str(row.get("_id") or row.get("id") or uuid.uuid4()),
        "sender_id": address,
        "raw_text": body,
    }


def cmd_pull(args: argparse.Namespace) -> None:
    _ensure_dirs()
    device = adb_client.ensure_device_accessible(args.serial)
    print(f"Using device {device.serial} ({device.model or 'unknown model'})")
    rows, method = adb_client.pull_sms(device)
    normalized = [r for r in (_normalize_pulled_row(row) for row in rows) if r is not None]

    out_path = _RAW_DIR / f"sms_raw_{_timestamp()}.json"
    out_path.write_text(json.dumps(normalized, indent=2))
    print(f"Pulled {len(normalized)} SMS via {method} -> {out_path}")
    print("(raw file is git-ignored and contains unredacted SMS text - never commit it)")


def cmd_sanitize(args: argparse.Namespace) -> None:
    _ensure_dirs()
    input_path = Path(args.input) if args.input else _latest_file(_RAW_DIR, "sms_raw_*.json")
    if not input_path or not input_path.exists():
        print("No raw pull found - run `pipenv run sms-pull` first.", file=sys.stderr)
        sys.exit(1)

    raw_messages = json.loads(input_path.read_text())
    sanitized = [
        {"id": m["id"], "sender_id": m["sender_id"], "sanitized_text": sanitize(m["raw_text"])} for m in raw_messages
    ]
    out_path = _SANITIZED_DIR / f"sms_sanitized_{_timestamp()}.json"
    out_path.write_text(json.dumps(sanitized, indent=2))
    print(f"Sanitized {len(sanitized)} SMS -> {out_path}")


def _load_latest_sanitized() -> list[dict]:
    path = _latest_file(_SANITIZED_DIR, "sms_sanitized_*.json")
    if not path:
        print("No sanitized corpus found - run `pipenv run sms-sanitize` first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text())


def cmd_validate(args: argparse.Namespace) -> None:
    _ensure_dirs()
    if args.pull:
        cmd_pull(args)
        cmd_sanitize(args)
    messages = _load_latest_sanitized()
    results = report_mod.parse_sanitized_messages(messages)
    report_mod.print_report(results)

    out_path = _REPORTS_DIR / f"report_{_timestamp()}.json"
    out_path.write_text(json.dumps([r.__dict__ for r in results], indent=2))
    print(f"\nFull report written to {out_path}")


def cmd_review(args: argparse.Namespace) -> None:
    _ensure_dirs()
    messages = _load_latest_sanitized()
    results = report_mod.parse_sanitized_messages(messages)
    low_confidence = [r for r in results if r.is_transaction and r.confidence < report_mod.LOW_CONFIDENCE_THRESHOLD]

    if not low_confidence:
        print("No low-confidence transactional messages to review.")
        return

    corrections = []
    for r in low_confidence:
        print("\n" + "=" * 60)
        print(f"sender={r.sender_id} type={r.transaction_type} confidence={r.confidence:.2f}")
        print(f"text: {r.sanitized_text}")
        print(f"amount={r.amount} merchant={r.merchant} bank={r.bank_code}")
        print(f"evidence: {'; '.join(r.evidence)}")
        choice = input("[c]orrect / [i]ncorrect / [e]dit / [s]kip / [q]uit: ").strip().lower()

        if choice == "q":
            break
        if choice == "s":
            continue

        correction: dict = {"message_id": r.message_id, "sender_id": r.sender_id, "sanitized_text": r.sanitized_text}
        if choice == "c":
            correction["verdict"] = "correct"
            correction["expected"] = {
                "is_transaction": True,
                "transaction_type": r.transaction_type,
                "amount": r.amount,
                "merchant": r.merchant,
            }
        elif choice == "i":
            correction["verdict"] = "incorrect"
        elif choice == "e":
            amount = input(f"  amount [{r.amount}]: ").strip() or r.amount
            merchant = input(f"  merchant [{r.merchant}]: ").strip() or r.merchant
            txn_type = input(f"  transaction_type [{r.transaction_type}]: ").strip() or r.transaction_type
            correction["verdict"] = "edited"
            correction["expected"] = {
                "is_transaction": True,
                "transaction_type": txn_type,
                "amount": float(amount) if amount not in (None, "") else None,
                "merchant": merchant,
            }
        else:
            print("unrecognized choice, skipping")
            continue

        corrections.append(correction)

    out_path = _CORRECTIONS_DIR / f"corrections_{_timestamp()}.json"
    out_path.write_text(json.dumps(corrections, indent=2))
    print(f"\nSaved {len(corrections)} correction(s) -> {out_path}")


def cmd_promote_test(args: argparse.Namespace) -> None:
    _PROMOTED_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    correction_files = sorted(_CORRECTIONS_DIR.glob("corrections_*.json"))
    if not correction_files:
        print("No corrections found - run `pipenv run sms-review` first.", file=sys.stderr)
        sys.exit(1)

    promoted = 0
    for path in correction_files:
        for correction in json.loads(path.read_text()):
            if correction.get("verdict") not in ("correct", "edited"):
                continue
            fixture_id = correction["message_id"]
            fixture_path = _PROMOTED_FIXTURES_DIR / f"{fixture_id}.json"
            if fixture_path.exists():
                continue
            fixture_path.write_text(
                json.dumps(
                    {
                        "id": fixture_id,
                        "sender_id": correction["sender_id"],
                        "sanitized_text": correction["sanitized_text"],
                        "expected": correction["expected"],
                    },
                    indent=2,
                )
            )
            promoted += 1

    print(f"Promoted {promoted} new regression test fixture(s) into {_PROMOTED_FIXTURES_DIR}")
    print("Run `cd services/api/src && pipenv run pytest tests/test_sms_real_world_regression.py -v` to confirm.")


def cmd_evaluate(args: argparse.Namespace) -> None:
    correction_files = sorted(_CORRECTIONS_DIR.glob("corrections_*.json"))
    if not correction_files:
        print("No corrections found - run `pipenv run sms-review` first to build labeled ground truth.", file=sys.stderr)
        sys.exit(1)

    labels = []
    for path in correction_files:
        labels.extend(json.loads(path.read_text()))

    messages = [{"id": c["message_id"], "sender_id": c["sender_id"], "sanitized_text": c["sanitized_text"]} for c in labels]
    results = {r.message_id: r for r in report_mod.parse_sanitized_messages(messages)}

    total = len(labels)
    true_positive = false_positive = false_negative = 0
    amount_matches = amount_total = 0
    merchant_matches = merchant_total = 0
    type_matches = type_total = 0
    low_confidence = 0

    for correction in labels:
        result = results.get(correction["message_id"])
        if result is None:
            continue
        expected_is_txn = correction["verdict"] in ("correct", "edited")

        if expected_is_txn and result.is_transaction:
            true_positive += 1
        elif not expected_is_txn and result.is_transaction:
            false_positive += 1
        elif expected_is_txn and not result.is_transaction:
            false_negative += 1

        if result.confidence < report_mod.LOW_CONFIDENCE_THRESHOLD:
            low_confidence += 1

        expected = correction.get("expected")
        if not expected:
            continue
        if expected.get("amount") is not None:
            amount_total += 1
            if result.amount == expected["amount"]:
                amount_matches += 1
        if expected.get("merchant") is not None:
            merchant_total += 1
            if result.merchant == expected["merchant"]:
                merchant_matches += 1
        if expected.get("transaction_type") is not None:
            type_total += 1
            if result.transaction_type == expected["transaction_type"]:
                type_matches += 1

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else float("nan")
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else float("nan")

    print("=== SMS parser evaluation (against reviewed ground truth) ===")
    print(f"labeled examples:              {total}")
    print(f"classification precision:      {precision:.2f}")
    print(f"classification recall:         {recall:.2f}")
    print(f"false positive rate (of {total:>3}): {false_positive / total if total else float('nan'):.2f}  <- minimize this (spec Part 21)")
    print(f"false negative rate (of {total:>3}): {false_negative / total if total else float('nan'):.2f}")
    print(f"amount exact-match accuracy:   {amount_matches}/{amount_total}")
    print(f"merchant accuracy:             {merchant_matches}/{merchant_total}")
    print(f"transaction-type accuracy:     {type_matches}/{type_total}")
    print(f"low-confidence rate:           {low_confidence}/{total}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sms_dev", description=__doc__)
    parser.add_argument("--serial", help="ADB device serial (only needed if multiple devices are connected)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("pull", help="pull SMS from the connected device").set_defaults(func=cmd_pull)

    p_sanitize = sub.add_parser("sanitize", help="sanitize the latest (or a given) raw pull")
    p_sanitize.add_argument("--input", help="path to a specific raw pull JSON file")
    p_sanitize.set_defaults(func=cmd_sanitize)

    p_validate = sub.add_parser("validate", help="pull -> sanitize -> parse -> print report")
    p_validate.add_argument("--pull", action="store_true", help="pull+sanitize fresh data before validating")
    p_validate.set_defaults(func=cmd_validate)

    sub.add_parser("review", help="interactively review low-confidence transactional messages").set_defaults(func=cmd_review)
    sub.add_parser("promote-test", help="turn reviewed-correct examples into regression test fixtures").set_defaults(
        func=cmd_promote_test
    )
    sub.add_parser("evaluate", help="precision/recall/accuracy metrics against reviewed corrections").set_defaults(
        func=cmd_evaluate
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

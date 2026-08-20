"""Regression tests generated from *real, sanitized* SMS pulled off a
physical device via the dev ADB pipeline (spec Parts 16-20,
scripts/sms_dev/cli.py promote-test).

Each promoted fixture is a small JSON file in
tests/fixtures/real_world_promoted/ containing only sanitized text (no real
account numbers/UPI IDs/phone numbers/names - see scripts/sms_dev/sanitizer.py)
plus the parser output a human confirmed was correct at promotion time. This
file starts empty and stays empty until `sms-promote-test` has actually been
run against a connected device - that's expected, not a bug.
"""
import json
from pathlib import Path

import pytest

from shared.sms.pipeline import SmsParserPipeline
from shared.sms_parser_rules_seed import default_sms_parser_rules
from datetime import datetime, timezone

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "real_world_promoted"
_RULES = default_sms_parser_rules()


def _load_fixtures() -> list[dict]:
    if not _FIXTURES_DIR.is_dir():
        return []
    fixtures = []
    for path in sorted(_FIXTURES_DIR.glob("*.json")):
        with path.open() as f:
            fixtures.append(json.load(f))
    return fixtures


_FIXTURES = _load_fixtures()


@pytest.mark.skipif(not _FIXTURES, reason="no promoted real-world SMS fixtures yet - run `pipenv run sms-promote-test`")
@pytest.mark.parametrize("fixture", _FIXTURES, ids=[f.get("id", str(i)) for i, f in enumerate(_FIXTURES)])
def test_promoted_real_world_sms(fixture):
    pipeline = SmsParserPipeline()
    parsed = pipeline.parse(
        sender_id=fixture["sender_id"],
        raw_text=fixture["sanitized_text"],
        received_at=datetime.now(timezone.utc),
        rules=_RULES,
    )
    expected = fixture["expected"]

    assert parsed.is_transaction == expected["is_transaction"]
    assert parsed.transaction_type.value == expected["transaction_type"]
    if expected.get("amount") is not None:
        assert parsed.amount is not None
        assert parsed.amount.value == expected["amount"]
    if expected.get("merchant") is not None:
        assert parsed.merchant_raw is not None
        assert parsed.merchant_raw.value == expected["merchant"]

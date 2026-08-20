"""Tests for the dev-only ADB pipeline's `content query` output parser
(scripts/sms_dev/adb_client.py) - specifically that a multi-line SMS body
(common in real bank templates) survives intact instead of being truncated
at the first embedded newline (a real bug found via LED-18's own
real-device QA pass, see docs/sms_parser.md).
"""
from scripts.sms_dev.adb_client import _parse_content_query_output


def test_multiline_body_is_not_truncated():
    raw = (
        "Row: 0 _id=101, address=HDFCBK, date=1753650600000, thread_id=5, sub_id=1, "
        "body=Received!\nINR 100.0 in HDFC Bank A/c xx3842\nOn 28-07-26\n"
        "For IMPS -CASHFREE PAYMENTS ES-6209...\nAvl bal INR 44,308.51\n"
    )
    rows = _parse_content_query_output(raw)
    assert len(rows) == 1
    assert rows[0]["address"] == "HDFCBK"
    body = rows[0]["body"]
    assert "Received!" in body
    assert "INR 100.0 in HDFC Bank A/c xx3842" in body
    assert "For IMPS -CASHFREE PAYMENTS ES-6209..." in body
    assert "Avl bal INR 44,308.51" in body


def test_multiple_rows_with_multiline_bodies_stay_separate():
    raw = (
        "Row: 0 _id=1, address=HDFCBK, date=1000, thread_id=1, sub_id=1, "
        "body=Line one\nLine two for message one\n"
        "Row: 1 _id=2, address=AXISBK, date=2000, thread_id=2, sub_id=1, "
        "body=Line one\nLine two for message two\n"
    )
    rows = _parse_content_query_output(raw)
    assert len(rows) == 2
    assert rows[0]["address"] == "HDFCBK"
    assert "message one" in rows[0]["body"]
    assert rows[1]["address"] == "AXISBK"
    assert "message two" in rows[1]["body"]
    assert "message two" not in rows[0]["body"]


def test_body_containing_commas_is_preserved():
    raw = "Row: 0 _id=1, address=HDFCBK, date=1000, thread_id=1, sub_id=1, body=Rs.1,299.00 debited, thanks\n"
    rows = _parse_content_query_output(raw)
    assert rows[0]["body"] == "Rs.1,299.00 debited, thanks"

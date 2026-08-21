"""Unit tests for the layered SMS parser (shared/sms/*, LED-18) against the
synthetic corpus (spec Part 22) — no DB/HTTP involved, exercises
`SmsParserPipeline` directly.
"""
from datetime import datetime, timezone

from shared.sms.pipeline import SmsParserPipeline
from shared.sms_parser_rules_seed import default_sms_parser_rules
from tests.fixtures.synthetic_sms_corpus import CORPUS

_RULES = default_sms_parser_rules()
_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _parse(sender_id: str, raw_text: str):
    pipeline = SmsParserPipeline()
    return pipeline.parse(sender_id=sender_id, raw_text=raw_text, received_at=_NOW, rules=_RULES)


def test_corpus_classification_and_extraction():
    for entry in CORPUS:
        parsed = _parse(entry["sender_id"], entry["raw_text"])
        label = f"{entry['sender_id']}: {entry['raw_text']!r}"

        assert parsed.is_transaction == entry["is_transaction"], label
        assert parsed.transaction_type.value == entry["transaction_type"], label

        if not entry["is_transaction"]:
            continue

        if "amount" in entry:
            assert parsed.amount is not None, label
            assert parsed.amount.value == entry["amount"], label

        if "direction" in entry:
            assert parsed.direction() == entry["direction"], label

        if "merchant" in entry:
            assert parsed.merchant_raw is not None, label
            assert parsed.merchant_raw.value == entry["merchant"], label

        if entry.get("merchant_none"):
            assert parsed.merchant_raw is None, label
            assert parsed.counterparty is None, label

        if "counterparty" in entry:
            assert parsed.counterparty is not None, label
            assert parsed.counterparty.value == entry["counterparty"], label

        if "payment_method" in entry:
            assert parsed.payment_method is not None, label
            assert parsed.payment_method.value == entry["payment_method"], label

        if "last4" in entry:
            assert parsed.account_last4 is not None, label
            assert parsed.account_last4.value == entry["last4"], label

        if "transaction_id" in entry:
            assert parsed.transaction_id is not None, label
            assert parsed.transaction_id.value == entry["transaction_id"], label


def test_never_confuses_balance_for_transaction_amount():
    parsed = _parse("HDFCBK", "Rs.450.00 debited from A/c XX1234 at SWIGGY BANGALORE on 01-Jan-24. Avl Bal Rs.25430")
    assert parsed.amount.value == 450.0
    assert parsed.balance_after is not None
    assert parsed.balance_after.value == 25430.0


def test_never_confuses_credit_limit_for_transaction_amount():
    parsed = _parse("AXISBK", "Card used for INR 1,299 at CAFE. Available limit INR 48,701")
    assert parsed.amount.value == 1299.0
    assert parsed.credit_limit is not None
    assert parsed.credit_limit.value == 48701.0


def test_indian_digit_grouping_parses_correctly():
    parsed = _parse("SBIINB", "Rs.1,29,999.00 debited from A/c XX9988 at BIG PURCHASE on 20-Jan-24. Avl Bal Rs.500")
    assert parsed.amount.value == 129999.0


def test_otp_never_becomes_a_transaction_even_with_an_amount():
    parsed = _parse("HDFCBK", "123456 is your OTP to authorize a payment of Rs.10000. Do not share this with anyone.")
    assert parsed.is_transaction is False
    assert parsed.transaction_type.value == "otp"


def test_sender_id_with_dlt_prefix_and_suffix_still_resolves_bank():
    # Real-world finding (LED-18): carriers send the same bank under sender
    # IDs like "VM-HDFCBK-T"/"AD-HDFCBK-S" (DLT prefix *and* a trailing
    # category suffix), not just the bare "HDFCBK" the seed data lists.
    parsed = _parse("VM-HDFCBK-T", "Rs.450.00 debited from A/c XX1234 at SWIGGY BANGALORE on 01-Jan-24. Avl Bal Rs.5000")
    assert parsed.bank_code == "HDFC"
    assert parsed.institution_confidence >= 0.6


def test_amount_without_currency_symbol_still_extracted():
    # Real-world finding (LED-18): some bank templates (ICICI) never
    # include Rs./INR/₹ at all - "...credited with amount 1.75 .Ref...".
    parsed = _parse("ICICIT", "Your account XXXXXXXX1234 has been credited with amount 1.75 .Ref no- ABC123456 .Thanks")
    assert parsed.amount is not None
    assert parsed.amount.value == 1.75


def test_sub_rupee_amount_without_leading_zero_is_extracted():
    # Real-world finding (LED-18): ICICI formats sub-rupee credits with no
    # leading zero - "amount .91" rather than "amount 0.91".
    parsed = _parse("ICICIT", "Your account XXXXXXXX1234 has been credited with amount .91 .Ref no- ABC123456 .Thanks")
    assert parsed.amount is not None
    assert parsed.amount.value == 0.91


def test_upi_used_as_a_common_noun_does_not_false_positive_a_transaction_id():
    # Real-world finding (LED-18): "...has been used for a UPI transaction
    # of INR 291.17 at Dominos Pizza..." used to match the "UPI ref"
    # pattern with the capture landing on the word "transaction" itself,
    # since every label component after "UPI" was optional. 20 unrelated
    # ZET card transactions on the real device collapsed onto one
    # duplicate-fingerprint ("transaction") before this was fixed.
    parsed = _parse(
        "ZETPAY",
        "Dear Customer, your SBM ZET Credit card ending with 4679 has been used for a UPI transaction "
        "of INR 291.17 at Dominos Pizza on 20-Aug-26. Ref REALREF478009. SBM Bank India.",
    )
    assert parsed.transaction_id is not None
    assert parsed.transaction_id.value == "REALREF478009"


def test_bare_upi_handle_without_vpa_keyword_is_extracted():
    # Real-world finding (LED-18): Kotak's UPI-sent template never says the
    # literal word "VPA" - "Sent Rs.X ... to <handle>@<bank> on ..." - which
    # the VPA-keyword-gated pattern alone missed on ~91 real messages.
    parsed = _parse("KOTAKB", "Sent Rs.1.89 from Kotak Bank AC X3737 to somebody123@oksbi on 02-Aug-26.UPI Ref REF883164.")
    assert parsed.merchant_raw is not None or parsed.counterparty is not None
    value = (parsed.merchant_raw or parsed.counterparty).value
    assert value == "somebody123"


def test_not_completed_phrasing_classifies_as_failed_not_refund():
    # Real-world finding (LED-18, human-reviewed via scripts/sms_dev):
    # "Payment...was not completed. Any amount if debited will be refunded
    # in 4-7 days" describes a failed/conditional attempt, not a completed
    # refund - it must not be labeled REFUND just because the word
    # "refunded" also appears later in the same sentence.
    parsed = _parse("SWIGGY", "Payment Alert : Your payment for order #123 was not completed. Any amount if debited will be refunded in 4-7 days.")
    assert parsed.transaction_type.value == "failed_transaction"


def test_low_confidence_when_evidence_is_thin():
    # No sender-ID match, no bank name in the body, no account pattern -
    # institution confidence (and therefore overall confidence) should stay
    # low rather than confidently guessing a bank.
    parsed = _parse("UNKNOWNSENDER", "Rs.500 debited for a purchase.")
    assert parsed.institution_confidence < 0.5


def test_null_fields_are_not_guessed():
    parsed = _parse("HDFCBK", "Rs.500 debited.")
    assert parsed.account_last4 is None
    assert parsed.transaction_id is None
    assert parsed.merchant_raw is None

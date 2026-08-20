"""Tests for the dev-only ADB pipeline's sanitizer (spec Part 17) -
determinism, and that amount/direction/merchant/bank-name/structure survive
untouched while PII gets redacted.
"""
from scripts.sms_dev.sanitizer import sanitize


def test_sanitize_is_deterministic():
    text = "Your A/c XX1234 is debited by Rs 1,299 at AMAZON. UPI Ref 123456789012."
    assert sanitize(text) == sanitize(text)


def test_sanitize_redacts_account_ref_and_preserves_transaction_shape():
    text = "Your A/c XX1234 is debited by Rs 1,299 at AMAZON. UPI Ref 123456789012."
    sanitized = sanitize(text)

    assert "XX1234" not in sanitized
    assert "123456789012" not in sanitized
    assert "XX0000" in sanitized
    assert "Rs 1,299" in sanitized
    assert "debited" in sanitized
    assert "AMAZON" in sanitized


def test_sanitize_redacts_email_and_phone():
    text = "Contact rahul.sharma@gmail.com or 9876543210 for support."
    sanitized = sanitize(text)
    assert "rahul.sharma@gmail.com" not in sanitized
    assert "9876543210" not in sanitized
    assert "@example.com" in sanitized


def test_sanitize_redacts_upi_vpa_handle():
    text = "Paid Rs 500 to VPA amazon@icici for order."
    sanitized = sanitize(text)
    assert "amazon@icici" not in sanitized
    assert "@upi" in sanitized


def test_sanitize_redacts_counterparty_name_but_not_merchant():
    person_text = "Paid Rs 500 to Rahul Sharma via Google Pay."
    sanitized_person = sanitize(person_text)
    assert "Rahul Sharma" not in sanitized_person
    assert "PERSON" in sanitized_person

    merchant_text = "Paid Rs 500 to Swiggy via Google Pay."
    sanitized_merchant = sanitize(merchant_text)
    assert "Swiggy" in sanitized_merchant

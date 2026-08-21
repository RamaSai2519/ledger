"""Synthetic SMS test corpus (spec Part 22) — all values here are made up,
not real personal data. Covers every bank in `sms_parser_rules_seed.py`,
the major UPI/payment apps, and the full transaction-category list from the
spec so `tests/test_sms_parsing_pipeline.py` can exercise the pipeline
end-to-end without any DB/network dependency.

Each entry is a dict:
    sender_id, raw_text, is_transaction, transaction_type (spec enum value),
    and, when is_transaction, the subset of extracted fields worth pinning
    down (amount/direction/merchant/last4/payment_method/transaction_id).
"""
from __future__ import annotations

CORPUS: list[dict] = [
    # ── Banks: debit ──────────────────────────────────────────────────
    {
        "sender_id": "HDFCBK",
        "raw_text": "Rs.450.00 debited from A/c XX1234 at SWIGGY BANGALORE on 01-Jan-24. Avl Bal Rs.5000",
        "is_transaction": True,
        "transaction_type": "debit",
        "amount": 450.0,
        "direction": "debit",
        "merchant": "SWIGGY BANGALORE",
        "last4": "1234",
    },
    {
        "sender_id": "AXISBK",
        "raw_text": "INR 1200 debited from Card ending 5678 at AMAZON RETAIL on 02-Jan-24. Avl Bal Rs.3000",
        "is_transaction": True,
        "transaction_type": "card_payment",
        "amount": 1200.0,
        "direction": "debit",
        "merchant": "AMAZON RETAIL",
        "last4": "5678",
    },
    {
        "sender_id": "KOTAKB",
        "raw_text": "Rs.780.00 spent on Kotak Bank Card XX4321 at RELIANCE FRESH on 04-Jan-24. Avl Bal Rs.15000",
        "is_transaction": True,
        "transaction_type": "card_payment",
        "amount": 780.0,
        "direction": "debit",
        "merchant": "RELIANCE FRESH",
    },
    {
        "sender_id": "ZETPAY",
        "raw_text": "Rs.999.00 debited from Zet Card XX6677 at NETFLIX on 05-Jan-24. Avl Bal Rs.20000",
        "is_transaction": True,
        "transaction_type": "card_payment",
        "amount": 999.0,
        "direction": "debit",
        "merchant": "NETFLIX",
    },
    {
        "sender_id": "AMZNPL",
        "raw_text": "INR 350.00 spent on Amazon Pay Later A/c XX0099 at AMAZON on 06-Jan-24. Avl Bal Rs.5000",
        "is_transaction": True,
        "transaction_type": "debit",
        "amount": 350.0,
        "direction": "debit",
        "merchant": "AMAZON",
    },
    {
        "sender_id": "JUPCC",
        "raw_text": "Rs.1450.00 spent on Jupiter Card XX5566 at BIGBASKET on 07-Jan-24. Avl Bal Rs.8000",
        "is_transaction": True,
        "transaction_type": "card_payment",
        "amount": 1450.0,
        "direction": "debit",
        "merchant": "BIGBASKET",
    },
    # ── Banks: credit ─────────────────────────────────────────────────
    {
        "sender_id": "SBIINB",
        "raw_text": "Rs.2000.00 credited to A/c XX9988 from RAMA SATHYA on 03-Jan-24. Avl Bal Rs.10000",
        "is_transaction": True,
        "transaction_type": "credit",
        "amount": 2000.0,
        "direction": "credit",
    },
    {
        "sender_id": "CANBNK",
        "raw_text": "Rs.3000.00 credited to A/c XX7788 from EMPLOYER PVT LTD on 08-Jan-24. Avl Bal Rs.25000",
        "is_transaction": True,
        "transaction_type": "credit",
        "amount": 3000.0,
        "direction": "credit",
        "merchant": "EMPLOYER PVT LTD",
    },
    # ── UPI / payment apps ────────────────────────────────────────────
    {
        "sender_id": "KOTAKB",
        "raw_text": "Sent Rs.250.00 from Kotak Bank AC X4321 to BIGBASKET on 09-Jan-24 via UPI Ref 998877. Avl Bal Rs.14750",
        "is_transaction": True,
        "transaction_type": "upi_payment",
        "amount": 250.0,
        "direction": "debit",
        "merchant": "BIGBASKET",
        "transaction_id": "998877",
    },
    {
        "sender_id": "HDFCBK",
        "raw_text": "Rs 500 credited to A/c XX1234 via UPI from RAHUL SHARMA. Ref No 445566778899.",
        "is_transaction": True,
        "transaction_type": "upi_receipt",
        "amount": 500.0,
        "direction": "credit",
    },
    {
        "sender_id": "AXISBK",
        "raw_text": "Paid Rs 199 to Rahul Sharma via Google Pay. UPI Ref 112233445566.",
        "is_transaction": True,
        "transaction_type": "upi_payment",
        "amount": 199.0,
        "direction": "debit",
        "counterparty": "Rahul Sharma",
        "payment_method": "Google Pay",
    },
    {
        "sender_id": "AXISBK",
        "raw_text": "Paid Rs 349 to Swiggy via Google Pay. UPI Ref 998811223344.",
        "is_transaction": True,
        "transaction_type": "upi_payment",
        "amount": 349.0,
        "direction": "debit",
        "merchant": "Swiggy",
        "payment_method": "Google Pay",
    },
    {
        "sender_id": "HDFCBK",
        "raw_text": "Rs.120 paid to PAYTM MALL via PhonePe on 10-Jan-24.",
        "is_transaction": True,
        "transaction_type": "upi_payment",
        "amount": 120.0,
        "direction": "debit",
        "payment_method": "PhonePe",
    },
    {
        "sender_id": "SBIINB",
        "raw_text": "Rs.75 paid via BHIM UPI to CHAIWALA STORE. Ref 334455667788.",
        "is_transaction": True,
        "transaction_type": "upi_payment",
        "amount": 75.0,
        "direction": "debit",
        "payment_method": "BHIM",
    },
    # ── IMPS / NEFT / RTGS ────────────────────────────────────────────
    {
        "sender_id": "HDFCBK",
        "raw_text": "Rs.5000 debited from A/c XX1234 towards IMPS transfer to VENDOR SERVICES on 11-Jan-24. Avl Bal Rs.20000",
        "is_transaction": True,
        "transaction_type": "imps",
        "amount": 5000.0,
        "direction": "debit",
    },
    {
        "sender_id": "AXISBK",
        "raw_text": "Rs.15000 debited from A/c XX5678 via NEFT to LANDLORD RENT on 12-Jan-24. Avl Bal Rs.30000",
        "is_transaction": True,
        "transaction_type": "neft",
        "amount": 15000.0,
        "direction": "debit",
    },
    {
        "sender_id": "SBIINB",
        "raw_text": "Rs.200000 debited from A/c XX9988 via RTGS to BUILDER ESCROW on 13-Jan-24. Avl Bal Rs.50000",
        "is_transaction": True,
        "transaction_type": "rtgs",
        "amount": 200000.0,
        "direction": "debit",
    },
    {
        # LED-26 regression: IMPS/NEFT/RTGS are transfer *channels*, not
        # directions - a "Received" IMPS message must resolve to credit, not
        # silently default to debit just because it isn't UPI/card wording.
        "sender_id": "HDFCBK",
        "raw_text": "Received!\nRs.21.42 in HDFC Bank A/c xx3842\nOn 21-08-26\nFor IMPS -SOME SENDER- 623319977679\nAvl bal Rs.442.64",
        "is_transaction": True,
        "transaction_type": "imps",
        "amount": 21.42,
        "direction": "credit",
    },
    # ── ATM / cash ────────────────────────────────────────────────────
    {
        "sender_id": "HDFCBK",
        "raw_text": "Rs.2000 withdrawn from ATM using Card XX1234 on 14-Jan-24. Avl Bal Rs.8000",
        "is_transaction": True,
        "transaction_type": "atm_withdrawal",
        "amount": 2000.0,
        "direction": "debit",
    },
    {
        "sender_id": "SBIINB",
        "raw_text": "Rs.10000 cash deposited to A/c XX9988 on 15-Jan-24. Avl Bal Rs.18000",
        "is_transaction": True,
        "transaction_type": "cash_deposit",
        "amount": 10000.0,
        "direction": "credit",
    },
    # ── Refund / reversal / failed / pending ─────────────────────────
    {
        "sender_id": "AXISBK",
        "raw_text": "Rs.499 refunded to A/c XX5678 for order #4521 on 16-Jan-24. Avl Bal Rs.12000",
        "is_transaction": True,
        "transaction_type": "refund",
        "amount": 499.0,
    },
    {
        "sender_id": "HDFCBK",
        "raw_text": "Your transaction of Rs.300 at CAFE MOCHA on 17-Jan-24 has been reversed. Avl Bal Rs.9000",
        "is_transaction": True,
        "transaction_type": "reversal",
        "amount": 300.0,
    },
    {
        "sender_id": "SBIINB",
        "raw_text": "Your payment of Rs.750 to MERCHANT XYZ has failed. Avl Bal Rs.14000",
        "is_transaction": True,
        "transaction_type": "failed_transaction",
        "amount": 750.0,
    },
    {
        "sender_id": "KOTAKB",
        "raw_text": "Your transaction of Rs.1200 is pending confirmation from the merchant.",
        "is_transaction": True,
        "transaction_type": "pending_transaction",
        "amount": 1200.0,
    },
    # ── Salary / EMI / fee / interest / autopay ──────────────────────
    {
        "sender_id": "HDFCBK",
        "raw_text": "Rs.55000 credited to A/c XX1234 as salary from ACME CORP on 01-Feb-24. Avl Bal Rs.60000",
        "is_transaction": True,
        "transaction_type": "salary",
        "amount": 55000.0,
        "direction": "credit",
    },
    {
        "sender_id": "AXISBK",
        "raw_text": "Rs.3200 debited from A/c XX5678 towards EMI for loan LN1234 on 05-Feb-24. Avl Bal Rs.7000",
        "is_transaction": True,
        "transaction_type": "emi_payment",
        "amount": 3200.0,
        "direction": "debit",
    },
    {
        "sender_id": "HDFCBK",
        "raw_text": "Rs.50 fee debited from A/c XX1234 for cash withdrawal on 06-Feb-24. Avl Bal Rs.4950",
        "is_transaction": True,
        "transaction_type": "fee",
        "amount": 50.0,
        "direction": "debit",
    },
    {
        "sender_id": "SBIINB",
        "raw_text": "Rs.120 interest credited to A/c XX9988 for the quarter ending Mar-24. Avl Bal Rs.14120",
        "is_transaction": True,
        "transaction_type": "interest",
        "amount": 120.0,
        "direction": "credit",
    },
    {
        "sender_id": "HDFCBK",
        "raw_text": "Rs.999 debited from A/c XX1234 via autopay for NETFLIX on 07-Feb-24. Avl Bal Rs.6000",
        "is_transaction": True,
        "transaction_type": "autopay",
        "amount": 999.0,
        "direction": "debit",
        "merchant": "NETFLIX",
    },
    {
        # Real-world finding (LED-18, pulled via scripts/sms_dev from a
        # live device, values replaced with synthetic ones here): ICICI's
        # actual template glues a constant internal code directly onto
        # "Ref" with no separator, then gives the real reference after
        # "no-". Regression test for the transaction_id.py fix that keeps
        # the boilerplate word from being extracted as if it were the
        # (supposedly unique) transaction ID.
        "sender_id": "ICICIT",
        "raw_text": "Dear CUSTOMER NAME ,Your account XXXXXXXX1234 has been credited with amount 1.75 .RefBOILERPLATE no- CMS5411823008 .Thanks",
        "is_transaction": True,
        "transaction_type": "credit",
        "amount": 1.75,
        "direction": "credit",
        "transaction_id": "CMS5411823008",
    },
    # ── Non-transaction: OTP / promo / statement / due reminder / balance ──
    {
        "sender_id": "HDFCBK",
        "raw_text": "123456 is your OTP for the transaction of Rs.5000. Do not share this with anyone.",
        "is_transaction": False,
        "transaction_type": "otp",
    },
    {
        "sender_id": "AXISBK",
        "raw_text": "Flat 50% OFF on your next order! Hurry, limited period offer. T&C apply.",
        "is_transaction": False,
        "transaction_type": "promotional",
    },
    {
        "sender_id": "HDFCBK",
        "raw_text": "Your credit card e-statement for Jan-24 has been generated. View it in the app.",
        "is_transaction": False,
        "transaction_type": "statement",
    },
    {
        "sender_id": "AXISBK",
        "raw_text": "Your credit card payment of Rs.5000 is due on 20-Feb-24. Kindly pay to avoid late fee.",
        "is_transaction": False,
        "transaction_type": "due_reminder",
    },
    {
        "sender_id": "SBIINB",
        "raw_text": "Your A/c XX9988 available balance is Rs.14120 as of 10-Feb-24.",
        "is_transaction": False,
        "transaction_type": "balance_only",
    },
    {
        "sender_id": "FRIEND1",
        "raw_text": "Hey, are we still on for dinner tonight?",
        "is_transaction": False,
        "transaction_type": "other",
    },
]

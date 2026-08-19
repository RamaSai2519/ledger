from datetime import datetime, timedelta, timezone

from bson import ObjectId

from jobs.sms_purge import run_sms_purge
from shared.db import get_sms_inbox_collection


def _sms_doc(**overrides):
    now = datetime.now(timezone.utc)
    doc = {
        "household_id": ObjectId(),
        "user_id": ObjectId(),
        "raw_text": "Rs.100 debited from A/c XX1111 at COFFEE SHOP on 01-Jan-24.",
        "sender_id": "HDFCBK",
        "received_at": now,
        "parse_status": "parsed",
        "parsed_amount": 100.0,
        "parsed_direction": "debit",
        "parsed_last4": "1111",
        "parsed_merchant": "COFFEE SHOP",
        "parsed_ref": None,
        "suggested_wallet_id": None,
        "suggested_category_id": None,
        "confidence_score": 0.5,
        "status": "suggested",
        "resolved_transaction_id": None,
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


def test_purge_nulls_raw_text_for_old_docs(client):
    old_time = datetime.now(timezone.utc) - timedelta(days=31)
    inbox = get_sms_inbox_collection()
    result = inbox.insert_one(_sms_doc(created_at=old_time))

    purged = run_sms_purge()
    assert result.inserted_id in purged

    doc = inbox.find_one({"_id": result.inserted_id})
    assert doc["raw_text"] is None
    # Structured parsed fields survive for audit history.
    assert doc["parsed_merchant"] == "COFFEE SHOP"
    assert doc["parsed_amount"] == 100.0


def test_purge_nulls_raw_text_for_resolved_docs_regardless_of_age(client):
    inbox = get_sms_inbox_collection()
    result = inbox.insert_one(_sms_doc(status="accepted"))

    purged = run_sms_purge()
    assert result.inserted_id in purged

    doc = inbox.find_one({"_id": result.inserted_id})
    assert doc["raw_text"] is None


def test_purge_leaves_recent_suggested_docs_untouched(client):
    inbox = get_sms_inbox_collection()
    result = inbox.insert_one(_sms_doc())

    purged = run_sms_purge()
    assert result.inserted_id not in purged

    doc = inbox.find_one({"_id": result.inserted_id})
    assert doc["raw_text"] is not None

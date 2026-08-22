import os
import sys

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "ledger_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

sys.path.insert(0, os.path.dirname(__file__))

from functools import lru_cache

import bcrypt
import mongomock
import pymongo
import pytest

import shared.db as db_module


@pytest.fixture(autouse=True)
def mock_mongo(monkeypatch):
    mock_client = mongomock.MongoClient()
    monkeypatch.setattr(pymongo, "MongoClient", lambda *a, **k: mock_client)
    db_module._client = None
    yield
    db_module._client = None


# bcrypt.hashpw is deliberately slow (~200ms/call at the default cost
# factor) and the suite calls it dozens of times via signup()/pin_set with
# the same handful of passwords ("password123" etc). Cache the real hash per
# password instead of re-deriving it every time — bcrypt.checkpw still
# verifies against a genuine hash, so this only removes redundant work, not
# coverage of the hashing/verification path itself.
_real_hashpw = bcrypt.hashpw


@lru_cache(maxsize=None)
def _cached_hashpw(password: bytes) -> bytes:
    return _real_hashpw(password, bcrypt.gensalt())


@pytest.fixture(autouse=True)
def _fast_bcrypt(monkeypatch):
    monkeypatch.setattr(bcrypt, "hashpw", lambda password, salt=None: _cached_hashpw(password))


@pytest.fixture
def client():
    from index import app

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def signup(client, mobile_number="9876543210", password="password123", name="Rama"):
    return client.post(
        "/auth/signup",
        json={"mobile_number": mobile_number, "password": password, "name": name},
    )


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}

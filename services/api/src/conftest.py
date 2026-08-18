import os
import sys

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "ledger_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

sys.path.insert(0, os.path.dirname(__file__))

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

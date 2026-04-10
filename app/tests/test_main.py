import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import Base
from main import app, get_db

engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_cache():
    with patch("main.cache_get", return_value=None), \
         patch("main.cache_set"), \
         patch("main.cache_delete"), \
         patch("main.redis_ping", return_value=False):
        yield


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def get_token(username="testuser", password="testpass"):
    client.post("/auth/register", json={"username": username, "password": password})
    resp = client.post("/auth/token", data={"username": username, "password": password})
    return resp.json()["access_token"]


def auth_headers(token=None):
    return {"Authorization": f"Bearer {token or get_token()}"}


# ── Health ────────────────────────────────────────────────────────────────────
def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ── Auth ──────────────────────────────────────────────────────────────────────
def test_register():
    r = client.post("/auth/register", json={"username": "alice", "password": "secret"})
    assert r.status_code == 201
    assert r.json()["username"] == "alice"


def test_register_duplicate():
    client.post("/auth/register", json={"username": "bob", "password": "pass"})
    r = client.post("/auth/register", json={"username": "bob", "password": "pass"})
    assert r.status_code == 400


def test_login():
    client.post("/auth/register", json={"username": "carol", "password": "pass"})
    r = client.post("/auth/token", data={"username": "carol", "password": "pass"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password():
    client.post("/auth/register", json={"username": "dave", "password": "right"})
    r = client.post("/auth/token", data={"username": "dave", "password": "wrong"})
    assert r.status_code == 401


# ── Items ─────────────────────────────────────────────────────────────────────
def test_items_require_auth():
    r = client.get("/items")
    assert r.status_code == 401


def test_create_item():
    r = client.post("/items", json={"name": "test", "description": "desc"},
                    headers=auth_headers())
    assert r.status_code == 201
    assert r.json()["name"] == "test"


def test_read_items():
    headers = auth_headers()
    client.post("/items", json={"name": "item1"}, headers=headers)
    client.post("/items", json={"name": "item2"}, headers=headers)
    r = client.get("/items", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_delete_item():
    headers = auth_headers()
    item_id = client.post("/items", json={"name": "to delete"}, headers=headers).json()["id"]
    assert client.delete(f"/items/{item_id}", headers=headers).status_code == 204
    assert all(i["id"] != item_id for i in client.get("/items", headers=headers).json())


def test_delete_nonexistent():
    assert client.delete("/items/99999", headers=auth_headers()).status_code == 404


def test_pagination():
    headers = auth_headers()
    for i in range(5):
        client.post("/items", json={"name": f"item {i}"}, headers=headers)
    assert len(client.get("/items?limit=2&skip=0", headers=headers).json()) == 2


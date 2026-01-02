from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_session
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_list_users_empty():
    with TestClient(app) as client:
        response = client.get("/users")

    assert response.status_code == 200
    assert response.json() == []


def test_create_user_and_list():
    payload = {
        "email": "user@example.com",
        "password": "supersecure",
        "role": "admin",
    }

    with TestClient(app) as client:
        create_response = client.post("/users", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["email"] == payload["email"]
    assert created["role"] == payload["role"]
    assert created["id"] > 0
    assert created["created_at"]

    with TestClient(app) as client:
        list_response = client.get("/users")

    assert list_response.status_code == 200
    users = list_response.json()
    assert len(users) == 1
    assert users[0]["email"] == payload["email"]


def test_create_user_duplicate_email_rejected():
    payload = {
        "email": "duplicate@example.com",
        "password": "uniquepassword",
        "role": "viewer",
    }

    with TestClient(app) as client:
        first = client.post("/users", json=payload)
        second = client.post("/users", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.json()["detail"] == "User already exists"

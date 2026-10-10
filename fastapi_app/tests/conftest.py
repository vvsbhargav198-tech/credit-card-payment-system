import os

os.environ["USE_SQLITE"] = "1"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-0123456789abcdef"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["PAYMENT_SUCCESS_RATE"] = "1.0"
os.environ["PAYMENT_PROCESSING_DELAY"] = "0"

from datetime import datetime, timedelta, timezone  

import jwt  
import pytest  
from fastapi.testclient import TestClient  

from app.config import settings  
from app.database import Base, SessionLocal, engine  
from app.main import app  
from app.models import Card, User  


def make_token(user_id, *, token_type="access", expires_in=300, secret=None):
    payload = {
        "user_id": user_id,
        "token_type": token_type,
        "jti": "test-jti",
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, secret or settings.jwt_secret_key, algorithm="HS256")


def bearer(user_id, **kwargs):
    return {"Authorization": f"Bearer {make_token(user_id, **kwargs)}"}


@pytest.fixture(autouse=True)
def database():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def user(db):
    u = User(id=1, is_active=True)
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def other_user(db):
    u = User(id=2, is_active=True)
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def card(db, user):
    c = Card(id=1, user_id=user.id, brand="VISA", last4="4242", expiry_month=12,
             expiry_year=datetime.now().year + 2)
    db.add(c)
    db.commit()
    return c


@pytest.fixture
def auth(user):
    return bearer(user.id)

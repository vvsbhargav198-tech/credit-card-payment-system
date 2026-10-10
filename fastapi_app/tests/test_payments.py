from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models import Card, Transaction
from app.schemas import PaymentRequest
from app.services.payments import create_pending_transaction, finalize_transaction
from app.services.simulator import GatewayResult

from .conftest import bearer, make_token

URL = "/payments"


def pay(client, headers, **overrides):
    body = {"card_id": 1, "amount": "49.99", "currency": "USD", "description": "Order #1"}
    body.update(overrides)
    return client.post(URL, json=body, headers=headers)


def txn_count(db):
    return db.scalar(select(func.count()).select_from(Transaction))


# ------------------------------------------------------------------ basics
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_swagger_and_openapi_are_enabled(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/payments" in schema["paths"]


# ------------------------------------------------------------------ authentication
def test_requires_token(client, card):
    assert client.post(URL, json={"card_id": 1, "amount": "5"}).status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer garbage"},
        {"Authorization": "Basic abc"},
        bearer(1, expires_in=-10),                       # expired
        bearer(1, secret="a-completely-different-secret-key-0123456789"),  # wrong signature
        bearer(1, token_type="refresh"),                # refresh token must not work
    ],
)
def test_bad_tokens_rejected(client, user, card, db, headers):
    response = pay(client, headers)
    assert response.status_code == 401
    assert txn_count(db) == 0


def test_token_without_user_id_rejected(client, card):
    import jwt
    from datetime import timezone

    token = jwt.encode(
        {"token_type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.jwt_secret_key, algorithm="HS256",
    )
    assert pay(client, {"Authorization": f"Bearer {token}"}).status_code == 401


def test_unknown_or_inactive_user_rejected(client, db, user, card):
    assert pay(client, bearer(999)).status_code == 401
    user.is_active = False
    db.commit()
    assert pay(client, bearer(user.id)).status_code == 401


# ------------------------------------------------------------------ happy path & failures
def test_successful_payment(client, db, auth, card):
    response = pay(client, auth)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["amount"] == "49.99"
    assert data["card_last4"] == "4242"
    assert data["failure_reason"] == ""
    assert len(data["reference"]) == 36
    row = db.scalars(select(Transaction)).one()
    assert row.status == "SUCCESS" and row.user_id == 1 and row.card_id == 1
    assert row.created_at <= row.updated_at


def test_declined_test_card_ends_as_failed(client, db, auth, user):
    db.add(Card(id=7, user_id=user.id, brand="VISA", last4="0002", expiry_month=12, expiry_year=datetime.now().year + 2))
    db.commit()
    response = pay(client, auth, card_id=7)
    assert response.status_code == 201
    assert response.json()["status"] == "FAILED"
    assert "declined" in response.json()["failure_reason"].lower()
    assert db.scalars(select(Transaction)).one().status == "FAILED"


def test_random_failure(client, auth, card, monkeypatch):
    monkeypatch.setattr(settings, "payment_success_rate", 0.0)
    assert pay(client, auth).json()["status"] == "FAILED"


def test_expired_card_fails(client, db, auth, user):
    db.add(Card(id=8, user_id=user.id, brand="VISA", last4="1111", expiry_month=1, expiry_year=datetime.now().year - 1))
    db.commit()
    data = pay(client, auth, card_id=8).json()
    assert data["status"] == "FAILED" and data["failure_reason"] == "Card has expired"


def test_amount_over_limit_fails(client, auth, card):
    assert pay(client, auth, amount="10000.01").json()["status"] == "FAILED"


def test_simulator_crash_never_leaves_payment_pending(client, db, auth, card, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("gateway exploded")

    monkeypatch.setattr("app.services.payments.simulate_gateway", boom)
    data = pay(client, auth).json()
    assert data["status"] == "FAILED"
    assert data["failure_reason"] == "Internal processing error"
    assert db.scalars(select(Transaction)).one().status == "FAILED"


def test_status_lifecycle_pending_then_final(db, user, card):
    payload = PaymentRequest(card_id=1, amount="20.00")
    txn = create_pending_transaction(db, user, card, payload)
    assert txn.status == "PENDING"
    db.expire_all()
    assert db.get(Transaction, txn.id).status == "PENDING"  

    finalize_transaction(db, txn, GatewayResult(True))
    assert db.get(Transaction, txn.id).status == "SUCCESS"

    other = create_pending_transaction(db, user, card, payload)
    finalize_transaction(db, other, GatewayResult(False, "nope"))
    assert db.get(Transaction, other.id).status == "FAILED"
    assert db.get(Transaction, other.id).failure_reason == "nope"


# ------------------------------------------------------------------ authorization
def test_cannot_pay_with_someone_elses_card(client, db, user, other_user):
    db.add(Card(id=5, user_id=other_user.id, brand="VISA", last4="1881", expiry_month=12, expiry_year=datetime.now().year + 2))
    db.commit()
    assert pay(client, bearer(user.id), card_id=5).status_code == 404
    assert txn_count(db) == 0


def test_unknown_card(client, auth, user, db):
    assert pay(client, auth, card_id=12345).status_code == 404
    assert txn_count(db) == 0


# ------------------------------------------------------------------ input validation
@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "10.999"},
        {"amount": "abc"},
        {"amount": "1000000.01"},
        {"currency": "XXX"},
        {"card_id": 0},
        {"card_id": "one"},
        {"description": "x" * 256},
        {"card_number": "4111111111111111"},   # card data must never be accepted here
        {"cvv": "123"},
    ],
)
def test_invalid_payloads_rejected(client, db, auth, card, overrides):
    assert pay(client, auth, **overrides).status_code == 422
    assert txn_count(db) == 0


def test_missing_fields_rejected(client, auth, card):
    assert client.post(URL, json={}, headers=auth).status_code == 422
    assert client.post(URL, json={"card_id": 1}, headers=auth).status_code == 422


def test_sql_injection_in_description_is_stored_as_plain_text(client, db, auth, card):
    evil = "x'); DROP TABLE transactions;--"
    response = pay(client, auth, description=evil)
    assert response.status_code == 201
    assert db.scalars(select(Transaction)).one().description == evil
    assert txn_count(db) == 1  # table still exists


def test_description_is_cleaned(client, auth, card):
    assert pay(client, auth, description="  hello\x00\x07 world  ").json()["description"] == "hello world"


# ------------------------------------------------------------------ status lookup
def test_get_payment_by_reference(client, auth, card, other_user):
    reference = pay(client, auth).json()["reference"]
    response = client.get(f"{URL}/{reference}", headers=auth)
    assert response.status_code == 200
    assert response.json()["reference"] == reference
    # another user cannot read it
    assert client.get(f"{URL}/{reference}", headers=bearer(other_user.id)).status_code == 404
    assert client.get(f"{URL}/does-not-exist", headers=auth).status_code == 404
    assert client.get(f"{URL}/{reference}").status_code == 401

import logging
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Card, Transaction, User, utcnow
from ..schemas import PaymentRequest
from .simulator import GatewayResult, simulate_gateway

logger = logging.getLogger("payments")


class CardNotFoundError(Exception):
    """Card does not exist OR belongs to someone else (deliberately indistinguishable)."""


def get_own_card(db: Session, user: User, card_id: int) -> Card:
    card = db.scalar(select(Card).where(Card.id == card_id, Card.user_id == user.id))
    if card is None:
        raise CardNotFoundError
    return card


def create_pending_transaction(db: Session, user: User, card: Card, payload: PaymentRequest) -> Transaction:
    """Step 1: persist the payment with status PENDING (committed, so it is visible immediately)."""
    now = utcnow()
    txn = Transaction(
        reference=str(uuid.uuid4()),
        user_id=user.id,
        card_id=card.id,
        card_last4=card.last4,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        status="PENDING",
        failure_reason="",
        created_at=now,
        updated_at=now,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def finalize_transaction(db: Session, txn: Transaction, result: GatewayResult) -> Transaction:
    """Step 3: move PENDING -> SUCCESS or FAILED."""
    txn.status = "SUCCESS" if result.success else "FAILED"
    txn.failure_reason = "" if result.success else result.reason[:255]
    txn.updated_at = utcnow()
    db.commit()
    db.refresh(txn)
    return txn


def process_payment(db: Session, user: User, payload: PaymentRequest) -> Transaction:
    card = get_own_card(db, user, payload.card_id)
    txn = create_pending_transaction(db, user, card, payload)

    try:
        if settings.payment_processing_delay > 0:
            time.sleep(settings.payment_processing_delay)  # pretend to talk to a bank
        result = simulate_gateway(
            amount=txn.amount,
            last4=card.last4,
            expiry_month=card.expiry_month,
            expiry_year=card.expiry_year,
        )
    except Exception:  # never leave a payment stuck in PENDING
        logger.exception("Gateway simulation crashed for transaction %s", txn.reference)
        result = GatewayResult(False, "Internal processing error")

    txn = finalize_transaction(db, txn, result)
    logger.info("Transaction %s finished with status %s", txn.reference, txn.status)
    return txn

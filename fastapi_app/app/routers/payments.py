from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Transaction, User
from ..schemas import PaymentRequest, PaymentResponse
from ..security import get_current_user
from ..services.payments import CardNotFoundError, process_payment

router = APIRouter(prefix="/payments", tags=["Payments"])

AUTH_ERRORS = {401: {"description": "Missing, invalid or expired token"}}


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Make a payment with a saved card",
    description=(
        "Creates a transaction with status **PENDING**, simulates the gateway, then sets the final status "
        "to **SUCCESS** or **FAILED**. A declined payment is still a created transaction (HTTP 201) - "
        "check the `status` field.\n\n"
        "Test cards (last 4 digits): `0002` always declined, `9995` insufficient funds."
    ),
    responses={**AUTH_ERRORS, 404: {"description": "Card not found (or not yours)"}},
)
def make_payment(
    payload: PaymentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return process_payment(db, user, payload)
    except CardNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")


@router.get(
    "/{reference}",
    response_model=PaymentResponse,
    summary="Get the status of one of my payments",
    responses={**AUTH_ERRORS, 404: {"description": "Payment not found (or not yours)"}},
)
def get_payment(
    reference: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    txn = db.scalar(select(Transaction).where(Transaction.reference == reference, Transaction.user_id == user.id))
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return txn

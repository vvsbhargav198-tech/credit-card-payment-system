from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from cards.models import Card
from transactions.models import Transaction

PASSWORD = "StrongPass#12345"


def create_user(username="alice", password=PASSWORD, **extra):
    extra.setdefault("email", f"{username}@example.com")
    return User.objects.create_user(username=username, password=password, **extra)


def create_admin(username="boss", password=PASSWORD):
    return User.objects.create_superuser(username=username, email=f"{username}@example.com", password=password)


def client_for(user) -> APIClient:
    """API client authenticated with a REAL signed JWT access token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


def create_card(user, last4="4242", brand="VISA", **extra):
    year = timezone.now().year + 3
    defaults = dict(
        cardholder_name="Alice Doe", brand=brand, card_type="CREDIT",
        masked_number=f"**** **** **** {last4}", last4=last4, expiry_month=12, expiry_year=year,
    )
    defaults.update(extra)
    return Card.objects.create(user=user, **defaults)


def create_transaction(user, card=None, amount="10.00", status="SUCCESS", days_ago=0, **extra):
    txn = Transaction.objects.create(
        user=user, card=card, card_last4=card.last4 if card else "0000",
        amount=Decimal(amount), status=status, **extra,
    )
    if days_ago:  
        Transaction.objects.filter(pk=txn.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
        txn.refresh_from_db()
    return txn

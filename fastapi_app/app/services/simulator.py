"""Fake payment gateway. Deterministic rules first, then a random outcome.

Test cards (last 4 digits):  0002 -> always declined,  9995 -> always 'insufficient funds'.
"""
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Optional

from ..config import settings


@dataclass(frozen=True)
class GatewayResult:
    success: bool
    reason: str = ""


def simulate_gateway(
    *,
    amount: Decimal,
    last4: str,
    expiry_month: int,
    expiry_year: int,
    now: Optional[datetime] = None,
    rng: Optional[Callable[[], float]] = None,
) -> GatewayResult:
    now = now or datetime.now(timezone.utc)
    rng = rng or random.random

    if (expiry_year, expiry_month) < (now.year, now.month):
        return GatewayResult(False, "Card has expired")
    if last4 == "0002":
        return GatewayResult(False, "Card declined by issuer (test card)")
    if last4 == "9995":
        return GatewayResult(False, "Insufficient funds (test card)")
    if amount > settings.single_payment_limit:
        return GatewayResult(False, "Amount exceeds the single-payment limit")
    if rng() < settings.payment_success_rate:
        return GatewayResult(True)
    return GatewayResult(False, "Payment declined by gateway (simulated)")

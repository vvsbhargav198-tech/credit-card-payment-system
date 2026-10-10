from datetime import datetime, timezone
from decimal import Decimal

from app.config import settings
from app.services.simulator import simulate_gateway

NOW = datetime(2026, 6, 15, tzinfo=timezone.utc)


def run(**overrides):
    args = dict(amount=Decimal("10.00"), last4="4242", expiry_month=12, expiry_year=2030, now=NOW, rng=lambda: 0.0)
    args.update(overrides)
    return simulate_gateway(**args)


def test_success_when_random_below_rate():
    assert run(rng=lambda: settings.payment_success_rate - 0.01).success is True


def test_failure_when_random_above_rate(monkeypatch):
    monkeypatch.setattr(settings, "payment_success_rate", 0.5)
    result = run(rng=lambda: 0.99)
    assert result.success is False
    assert "declined" in result.reason.lower()


def test_expired_card_fails():
    assert run(expiry_year=2026, expiry_month=5).reason == "Card has expired"


def test_card_valid_through_current_month():
    assert run(expiry_year=2026, expiry_month=6).success is True


def test_test_cards_have_fixed_outcomes():
    assert run(last4="0002").success is False
    assert "Insufficient" in run(last4="9995").reason


def test_amount_over_limit_fails():
    assert "limit" in run(amount=Decimal("10000.01")).reason
    assert run(amount=Decimal("10000.00")).success is True

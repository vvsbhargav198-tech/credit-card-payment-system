import uuid

from django.conf import settings
from django.db import models


def generate_reference() -> str:
    return str(uuid.uuid4())


class Transaction(models.Model):
    
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    reference = models.CharField(max_length=36, unique=True, default=generate_reference, editable=False)
    # PROTECT: financial records must not vanish when a user is deleted (deactivate instead).
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transactions")
    # SET_NULL + card_last4 snapshot: history survives card deletion.
    card = models.ForeignKey("cards.Card", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    card_last4 = models.CharField(max_length=4)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    description = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    failure_reason = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transactions"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.reference} {self.amount} {self.currency} [{self.status}]"

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Card(models.Model):
   
    class Brand(models.TextChoices):
        VISA = "VISA", "Visa"
        MASTERCARD = "MASTERCARD", "Mastercard"
        AMEX = "AMEX", "American Express"
        DISCOVER = "DISCOVER", "Discover"
        OTHER = "OTHER", "Other"

    class CardType(models.TextChoices):
        CREDIT = "CREDIT", "Credit"
        DEBIT = "DEBIT", "Debit"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cards")
    cardholder_name = models.CharField(max_length=100)
    brand = models.CharField(max_length=20, choices=Brand.choices)
    card_type = models.CharField(max_length=10, choices=CardType.choices)
    masked_number = models.CharField(max_length=19)
    last4 = models.CharField(max_length=4)
    expiry_month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    expiry_year = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cards"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.brand} {self.masked_number}"

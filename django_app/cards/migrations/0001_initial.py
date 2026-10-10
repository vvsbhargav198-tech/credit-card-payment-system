import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Card",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cardholder_name", models.CharField(max_length=100)),
                (
                    "brand",
                    models.CharField(
                        choices=[
                            ("VISA", "Visa"),
                            ("MASTERCARD", "Mastercard"),
                            ("AMEX", "American Express"),
                            ("DISCOVER", "Discover"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("card_type", models.CharField(choices=[("CREDIT", "Credit"), ("DEBIT", "Debit")], max_length=10)),
                ("masked_number", models.CharField(max_length=19)),
                ("last4", models.CharField(max_length=4)),
                (
                    "expiry_month",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(12),
                        ]
                    ),
                ),
                ("expiry_year", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "cards", "ordering": ["-created_at", "-id"]},
        ),
    ]

import django.db.models.deletion
import transactions.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cards", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "reference",
                    models.CharField(
                        default=transactions.models.generate_reference, editable=False, max_length=36, unique=True
                    ),
                ),
                ("card_last4", models.CharField(max_length=4)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("SUCCESS", "Success"), ("FAILED", "Failed")],
                        db_index=True,
                        default="PENDING",
                        max_length=10,
                    ),
                ),
                ("failure_reason", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "card",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="transactions",
                        to="cards.card",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "transactions", "ordering": ["-created_at", "-id"]},
        ),
    ]

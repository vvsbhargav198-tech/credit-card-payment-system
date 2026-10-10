from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate

from transactions.filters import filter_by_date_range
from transactions.models import Transaction


def daily_summary(date_from=None, date_to=None):
    
    money = DecimalField(max_digits=14, decimal_places=2)
    zero = Value(Decimal("0.00"), output_field=money)
    queryset = filter_by_date_range(Transaction.objects.all(), date_from, date_to)
    rows = (
        queryset.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            total=Count("id"),
            success_count=Count("id", filter=Q(status=Transaction.Status.SUCCESS)),
            failed_count=Count("id", filter=Q(status=Transaction.Status.FAILED)),
            pending_count=Count("id", filter=Q(status=Transaction.Status.PENDING)),
            total_amount=Coalesce(Sum("amount"), zero, output_field=money),
            success_amount=Coalesce(
                Sum("amount", filter=Q(status=Transaction.Status.SUCCESS)), zero, output_field=money
            ),
        )
        .order_by("-day")
    )
    cents = Decimal("0.01")
    result = []
    for row in rows:
        row["total_amount"] = Decimal(row["total_amount"]).quantize(cents)
        row["success_amount"] = Decimal(row["success_amount"]).quantize(cents)
        row["success_rate"] = round(row["success_count"] * 100 / row["total"], 1) if row["total"] else 0.0
        result.append(row)
    return result

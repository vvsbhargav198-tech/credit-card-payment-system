from datetime import datetime, time, timedelta, timezone

from rest_framework import serializers

from .models import Transaction

ORDERING_CHOICES = ["created_at", "-created_at", "amount", "-amount"]
FILTER_FIELDS = ("date_from", "date_to", "min_amount", "max_amount", "status", "ordering")


class TransactionFilterSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False, help_text="YYYY-MM-DD, inclusive")
    date_to = serializers.DateField(required=False, help_text="YYYY-MM-DD, inclusive")
    min_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=0)
    max_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=0)
    status = serializers.ChoiceField(choices=Transaction.Status.choices, required=False)
    ordering = serializers.ChoiceField(choices=ORDERING_CHOICES, required=False)

    def validate(self, attrs):
        if "date_from" in attrs and "date_to" in attrs and attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError({"date_to": "date_to must not be before date_from."})
        if "min_amount" in attrs and "max_amount" in attrs and attrs["min_amount"] > attrs["max_amount"]:
            raise serializers.ValidationError({"max_amount": "max_amount must not be below min_amount."})
        return attrs


def filter_by_date_range(queryset, date_from=None, date_to=None):
    
    if date_from:
        queryset = queryset.filter(created_at__gte=datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        queryset = queryset.filter(
            created_at__lt=datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )
    return queryset


def apply_filters(queryset, params):
    
    raw = {k: params.get(k) for k in FILTER_FIELDS if params.get(k) not in (None, "")}
    if isinstance(raw.get("status"), str):
        raw["status"] = raw["status"].upper()
    serializer = TransactionFilterSerializer(data=raw)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    queryset = filter_by_date_range(queryset, data.get("date_from"), data.get("date_to"))
    if "min_amount" in data:
        queryset = queryset.filter(amount__gte=data["min_amount"])
    if "max_amount" in data:
        queryset = queryset.filter(amount__lte=data["max_amount"])
    if "status" in data:
        queryset = queryset.filter(status=data["status"])
    if "ordering" in data:
        queryset = queryset.order_by(data["ordering"], "-id")
    return queryset

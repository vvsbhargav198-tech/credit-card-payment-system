from rest_framework import serializers

from accounts.models import User
from cards.models import Card

from .models import AdminLog


class AdminUserSerializer(serializers.ModelSerializer):
    

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "is_active", "is_staff", "date_joined", "last_login")
        read_only_fields = tuple(f for f in fields if f != "is_active")


class AdminCardSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Card
        fields = (
            "id", "user", "cardholder_name", "brand", "card_type", "masked_number",
            "last4", "expiry_month", "expiry_year", "created_at",
        )
        read_only_fields = fields


class AdminLogSerializer(serializers.ModelSerializer):
    admin = serializers.CharField(source="admin.username", read_only=True, default=None)

    class Meta:
        model = AdminLog
        fields = ("id", "admin", "action", "target_type", "target_id", "details", "ip_address", "created_at")
        read_only_fields = fields


class DailySummaryQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        if "date_from" in attrs and "date_to" in attrs and attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError({"date_to": "date_to must not be before date_from."})
        return attrs


class DailySummaryRowSerializer(serializers.Serializer):
    day = serializers.DateField()
    total = serializers.IntegerField()
    success_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    success_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    success_rate = serializers.FloatField()

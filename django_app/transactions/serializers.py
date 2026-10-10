from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    card_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id", "reference", "card_id", "card_last4", "amount", "currency",
            "description", "status", "failure_reason", "created_at", "updated_at",
        )
        read_only_fields = fields


class AdminTransactionSerializer(TransactionSerializer):
    user = serializers.CharField(source="user.username", read_only=True)

    class Meta(TransactionSerializer.Meta):
        fields = ("user",) + TransactionSerializer.Meta.fields
        read_only_fields = fields

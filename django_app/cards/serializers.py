import re

from django.utils import timezone
from rest_framework import serializers

from .models import Card
from .validators import (
    cvv_is_valid_for_brand,
    detect_brand,
    luhn_is_valid,
    mask_card_number,
    normalize_card_number,
)

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,99}$")


class CardSerializer(serializers.ModelSerializer):
    # write-only: accepted for validation, NEVER stored and NEVER returned
    card_number = serializers.CharField(write_only=True, max_length=25, style={"input_type": "password"})
    cvv = serializers.CharField(
        write_only=True,
        required=False,
        max_length=4,
        style={"input_type": "password"},
        help_text="Optional. Validated for format, then discarded - the CVV is never stored.",
    )

    class Meta:
        model = Card
        fields = (
            "id", "cardholder_name", "card_type", "card_number", "cvv",
            "expiry_month", "expiry_year", "brand", "masked_number", "last4", "created_at",
        )
        read_only_fields = ("id", "brand", "masked_number", "last4", "created_at")

    def validate_cardholder_name(self, value):
        value = " ".join(value.split())
        if not NAME_PATTERN.match(value):
            raise serializers.ValidationError("Name may contain only letters, spaces, apostrophes, dots and hyphens.")
        return value

    def validate_card_number(self, value):
        number = normalize_card_number(value)
        if not number or not 13 <= len(number) <= 19:
            raise serializers.ValidationError("Card number must contain 13 to 19 digits.")
        if not luhn_is_valid(number):
            raise serializers.ValidationError("Card number is not valid.")
        return number

    def validate(self, attrs):
        now = timezone.now()
        year, month = attrs["expiry_year"], attrs["expiry_month"]
        if (year, month) < (now.year, now.month):
            raise serializers.ValidationError({"expiry_year": "This card has expired."})
        if year > now.year + 20:
            raise serializers.ValidationError({"expiry_year": "Expiry year is too far in the future."})

        cvv = attrs.get("cvv")
        if cvv is not None and not cvv_is_valid_for_brand(cvv, detect_brand(attrs["card_number"])):
            raise serializers.ValidationError({"cvv": "CVV must be 3 digits (4 for American Express)."})
        return attrs

    def create(self, validated_data):
        number = validated_data.pop("card_number")
        validated_data.pop("cvv", None)  # discarded on purpose
        validated_data["brand"] = detect_brand(number)
        validated_data["last4"] = number[-4:]
        validated_data["masked_number"] = mask_card_number(number)
        return super().create(validated_data)

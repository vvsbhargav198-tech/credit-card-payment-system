import re

BRAND_VISA = "VISA"
BRAND_MASTERCARD = "MASTERCARD"
BRAND_AMEX = "AMEX"
BRAND_DISCOVER = "DISCOVER"
BRAND_OTHER = "OTHER"


def normalize_card_number(raw: str) -> str:
    
    cleaned = re.sub(r"[\s-]", "", raw or "")
    return cleaned if cleaned.isdigit() else ""


def luhn_is_valid(number: str) -> bool:
    
    if not number or not number.isdigit():
        return False
    total = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def detect_brand(number: str) -> str:
    
    if number.startswith("4"):
        return BRAND_VISA
    if 51 <= int(number[:2]) <= 55 or 2221 <= int(number[:4]) <= 2720:
        return BRAND_MASTERCARD
    if number[:2] in ("34", "37"):
        return BRAND_AMEX
    if number.startswith("6011") or number.startswith("65") or 644 <= int(number[:3]) <= 649:
        return BRAND_DISCOVER
    return BRAND_OTHER


def mask_card_number(number: str) -> str:
    
    return f"**** **** **** {number[-4:]}"


def cvv_is_valid_for_brand(cvv: str, brand: str) -> bool:
    expected = 4 if brand == BRAND_AMEX else 3
    return bool(re.fullmatch(r"\d+", cvv)) and len(cvv) == expected

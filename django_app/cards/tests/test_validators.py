from django.test import SimpleTestCase

from cards.validators import (
    cvv_is_valid_for_brand, detect_brand, luhn_is_valid, mask_card_number, normalize_card_number,
)


class ValidatorTests(SimpleTestCase):
    def test_luhn(self):
        for good in ("4111111111111111", "5555555555554444", "378282246310005", "6011111111111117"):
            self.assertTrue(luhn_is_valid(good), good)
        for bad in ("4111111111111112", "", "abcd", "0000000000000001"):
            self.assertFalse(luhn_is_valid(bad), bad)

    def test_brand_detection(self):
        self.assertEqual(detect_brand("4111111111111111"), "VISA")
        self.assertEqual(detect_brand("5555555555554444"), "MASTERCARD")
        self.assertEqual(detect_brand("2223003122003222"), "MASTERCARD")
        self.assertEqual(detect_brand("378282246310005"), "AMEX")
        self.assertEqual(detect_brand("6011111111111117"), "DISCOVER")
        self.assertEqual(detect_brand("9999999999999995"), "OTHER")

    def test_normalize(self):
        self.assertEqual(normalize_card_number("4111 1111-1111 1111"), "4111111111111111")
        self.assertEqual(normalize_card_number("4111 abcd"), "")
        self.assertEqual(normalize_card_number(""), "")

    def test_mask(self):
        self.assertEqual(mask_card_number("4111111111111111"), "**** **** **** 1111")

    def test_cvv(self):
        self.assertTrue(cvv_is_valid_for_brand("123", "VISA"))
        self.assertFalse(cvv_is_valid_for_brand("1234", "VISA"))
        self.assertTrue(cvv_is_valid_for_brand("1234", "AMEX"))
        self.assertFalse(cvv_is_valid_for_brand("12a", "VISA"))

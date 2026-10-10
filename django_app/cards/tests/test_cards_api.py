from django.utils import timezone
from rest_framework.test import APITestCase

from cards.models import Card
from testing_utils import client_for, create_card, create_user

URL = "/api/cards/"
FULL_NUMBER = "4111111111111111"


def card_payload(**overrides):
    data = {
        "cardholder_name": "Alice Doe", "card_type": "CREDIT", "card_number": "4111 1111 1111 1111",
        "cvv": "123", "expiry_month": 12, "expiry_year": timezone.now().year + 2,
    }
    data.update(overrides)
    return data


class AddCardTests(APITestCase):
    def setUp(self):
        self.user = create_user("alice")
        self.client = client_for(self.user)

    def test_add_card_returns_only_masked_data(self):
        response = self.client.post(URL, card_payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["masked_number"], "**** **** **** 1111")
        self.assertEqual(response.data["last4"], "1111")
        self.assertEqual(response.data["brand"], "VISA")
        self.assertNotIn("card_number", response.data)
        self.assertNotIn("cvv", response.data)
        self.assertNotIn(FULL_NUMBER, response.content.decode())

    def test_full_number_and_cvv_are_never_persisted(self):
        self.client.post(URL, card_payload(), format="json")
        field_names = {f.name for f in Card._meta.get_fields()}
        self.assertNotIn("card_number", field_names)
        self.assertNotIn("cvv", field_names)
        card = Card.objects.get()
        stored_values = " ".join(str(getattr(card, f.attname)) for f in Card._meta.concrete_fields)
        self.assertNotIn(FULL_NUMBER, stored_values)
        self.assertNotIn("123", card.masked_number)
        self.assertEqual(card.masked_number, "**** **** **** 1111")
        self.assertEqual(card.user, self.user)

    def test_cvv_is_optional(self):
        data = card_payload()
        del data["cvv"]
        self.assertEqual(self.client.post(URL, data, format="json").status_code, 201)

    def test_invalid_inputs_rejected(self):
        year = timezone.now().year
        cases = {
            "luhn": card_payload(card_number="4111111111111112"),
            "letters": card_payload(card_number="4111-abcd-1111-1111"),
            "too short": card_payload(card_number="4111"),
            "bad month": card_payload(expiry_month=13),
            "expired": card_payload(expiry_year=year - 1),
            "far future": card_payload(expiry_year=year + 40),
            "bad cvv": card_payload(cvv="12"),
            "amex-length cvv on visa": card_payload(cvv="1234"),
            "bad type": card_payload(card_type="GIFT"),
            "script in name": card_payload(cardholder_name="<script>alert(1)</script>"),
            "sql in name": card_payload(cardholder_name="Robert'); DROP TABLE cards;--"),
        }
        for label, data in cases.items():
            self.assertEqual(self.client.post(URL, data, format="json").status_code, 400, label)
        self.assertEqual(Card.objects.count(), 0)

    def test_expiry_this_month_is_still_valid(self):
        now = timezone.now()
        data = card_payload(expiry_month=now.month, expiry_year=now.year)
        self.assertEqual(self.client.post(URL, data, format="json").status_code, 201)

    def test_amex_requires_four_digit_cvv(self):
        data = card_payload(card_number="378282246310005", cvv="1234")
        response = self.client.post(URL, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["brand"], "AMEX")
        self.assertEqual(self.client.post(URL, card_payload(card_number="378282246310005"), format="json").status_code, 400)

    def test_requires_authentication(self):
        anonymous = self.client_class()
        self.assertEqual(anonymous.post(URL, card_payload(), format="json").status_code, 401)
        self.assertEqual(anonymous.get(URL).status_code, 401)


class ViewAndDeleteCardTests(APITestCase):
    def setUp(self):
        self.alice, self.bob = create_user("alice"), create_user("bob")
        self.alice_card = create_card(self.alice, "4242")
        self.bob_card = create_card(self.bob, "1881")
        self.client = client_for(self.alice)

    def test_list_shows_only_my_cards(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c["id"] for c in response.data["results"]], [self.alice_card.id])

    def test_retrieve_own_card(self):
        response = self.client.get(f"{URL}{self.alice_card.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["last4"], "4242")

    def test_cannot_see_or_delete_someone_elses_card(self):
        self.assertEqual(self.client.get(f"{URL}{self.bob_card.id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"{URL}{self.bob_card.id}/").status_code, 404)
        self.assertTrue(Card.objects.filter(pk=self.bob_card.pk).exists())

    def test_delete_own_card(self):
        self.assertEqual(self.client.delete(f"{URL}{self.alice_card.id}/").status_code, 204)
        self.assertFalse(Card.objects.filter(pk=self.alice_card.pk).exists())
        self.assertEqual(self.client.get(URL).data["count"], 0)

    def test_cards_cannot_be_edited(self):
        response = self.client.patch(f"{URL}{self.alice_card.id}/", {"last4": "9999"}, format="json")
        self.assertEqual(response.status_code, 405)

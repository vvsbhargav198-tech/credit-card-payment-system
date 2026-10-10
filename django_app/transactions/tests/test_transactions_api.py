import csv
import io

from rest_framework.test import APITestCase

from adminpanel.models import AdminLog
from testing_utils import client_for, create_admin, create_card, create_transaction, create_user

LIST = "/api/transactions/"
EXPORT = "/api/admin/transactions/export/"


class TransactionHistoryTests(APITestCase):
    def setUp(self):
        self.alice, self.bob = create_user("alice"), create_user("bob")
        card = create_card(self.alice)
        self.t_old = create_transaction(self.alice, card, "5.00", "FAILED", days_ago=10)
        self.t_mid = create_transaction(self.alice, card, "50.00", "SUCCESS", days_ago=5)
        self.t_new = create_transaction(self.alice, card, "500.00", "PENDING", days_ago=0)
        self.t_bob = create_transaction(self.bob, None, "99.00", "SUCCESS")
        self.client = client_for(self.alice)

    def ids(self, query=""):
        response = self.client.get(f"{LIST}{query}")
        self.assertEqual(response.status_code, 200, response.content)
        return [t["id"] for t in response.data["results"]]

    def test_requires_auth(self):
        self.assertEqual(self.client_class().get(LIST).status_code, 401)

    def test_only_my_transactions_newest_first(self):
        self.assertEqual(self.ids(), [self.t_new.id, self.t_mid.id, self.t_old.id])

    def test_filter_by_status_case_insensitive(self):
        self.assertEqual(self.ids("?status=success"), [self.t_mid.id])
        self.assertEqual(self.ids("?status=FAILED"), [self.t_old.id])

    def test_filter_by_amount(self):
        self.assertEqual(self.ids("?min_amount=10"), [self.t_new.id, self.t_mid.id])
        self.assertEqual(self.ids("?max_amount=50"), [self.t_mid.id, self.t_old.id])
        self.assertEqual(self.ids("?min_amount=10&max_amount=100"), [self.t_mid.id])

    def test_filter_by_date(self):
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.now().date()
        frm = (today - timedelta(days=6)).isoformat()
        self.assertEqual(self.ids(f"?date_from={frm}"), [self.t_new.id, self.t_mid.id])
        to = (today - timedelta(days=6)).isoformat()
        self.assertEqual(self.ids(f"?date_to={to}"), [self.t_old.id])

    def test_combined_filters_and_ordering(self):
        self.assertEqual(self.ids("?ordering=amount"), [self.t_old.id, self.t_mid.id, self.t_new.id])
        self.assertEqual(self.ids("?ordering=-amount&min_amount=10"), [self.t_new.id, self.t_mid.id])

    def test_invalid_filters_return_400(self):
        for query in ("?status=BOGUS", "?min_amount=abc", "?date_from=yesterday", "?ordering=password",
                      "?min_amount=-5", "?min_amount=10&max_amount=1", "?date_from=2030-01-02&date_to=2030-01-01"):
            self.assertEqual(self.client.get(f"{LIST}{query}").status_code, 400, query)

    def test_sql_injection_in_filters_is_rejected_not_executed(self):
        self.assertEqual(self.client.get(f"{LIST}?status=SUCCESS'%20OR%20'1'='1").status_code, 400)
        self.assertEqual(self.client.get(f"{LIST}?min_amount=1%20OR%201=1").status_code, 400)

    def test_detail_only_for_owner(self):
        self.assertEqual(self.client.get(f"{LIST}{self.t_mid.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"{LIST}{self.t_bob.id}/").status_code, 404)


class CsvExportTests(APITestCase):
    def setUp(self):
        self.admin = create_admin()
        self.alice = create_user("alice")
        card = create_card(self.alice)
        create_transaction(self.alice, card, "20.00", "SUCCESS", description="Coffee")
        create_transaction(self.alice, card, "30.00", "FAILED", description="=HYPERLINK(\"http://evil\")")

    def rows(self, response):
        return list(csv.reader(io.StringIO(response.content.decode())))

    def test_regular_user_forbidden(self):
        self.assertEqual(client_for(self.alice).get(EXPORT).status_code, 403)

    def test_anonymous_unauthorized(self):
        self.assertEqual(self.client_class().get(EXPORT).status_code, 401)

    def test_admin_downloads_csv_and_action_is_logged(self):
        response = client_for(self.admin).get(EXPORT)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        rows = self.rows(response)
        self.assertEqual(rows[0][:4], ["reference", "username", "email", "card_last4"])
        self.assertEqual(len(rows), 3)
        self.assertTrue(AdminLog.objects.filter(action="EXPORT_CSV", admin=self.admin).exists())

    def test_export_respects_filters(self):
        rows = self.rows(client_for(self.admin).get(f"{EXPORT}?status=FAILED"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][6], "FAILED")

    def test_export_invalid_filter_is_400(self):
        self.assertEqual(client_for(self.admin).get(f"{EXPORT}?status=nope").status_code, 400)

    def test_formula_injection_is_neutralised(self):
        rows = self.rows(client_for(self.admin).get(f"{EXPORT}?status=FAILED"))
        self.assertTrue(rows[1][8].startswith("'="))

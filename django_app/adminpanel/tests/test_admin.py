from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import User
from adminpanel.models import AdminLog
from adminpanel.services import daily_summary
from testing_utils import client_for, create_admin, create_card, create_transaction, create_user


class DailySummaryServiceTests(TestCase):
    def test_counts_and_amounts_per_day(self):
        user = create_user("alice")
        card = create_card(user)
        create_transaction(user, card, "10.00", "SUCCESS")
        create_transaction(user, card, "15.50", "SUCCESS")
        create_transaction(user, card, "100.00", "FAILED")
        create_transaction(user, card, "7.00", "PENDING")
        create_transaction(user, card, "1.00", "SUCCESS", days_ago=3)

        rows = daily_summary()
        self.assertEqual(len(rows), 2)
        today = rows[0]
        self.assertEqual(today["total"], 4)
        self.assertEqual(today["success_count"], 2)
        self.assertEqual(today["failed_count"], 1)
        self.assertEqual(today["pending_count"], 1)
        self.assertEqual(today["success_amount"], Decimal("25.50"))
        self.assertEqual(today["total_amount"], Decimal("132.50"))
        self.assertEqual(today["success_rate"], 50.0)
        self.assertEqual(rows[1]["success_amount"], Decimal("1.00"))

    def test_empty(self):
        self.assertEqual(daily_summary(), [])


class AdminApiTests(APITestCase):
    def setUp(self):
        self.admin = create_admin()
        self.alice = create_user("alice")
        self.card = create_card(self.alice)
        create_transaction(self.alice, self.card, "20.00", "SUCCESS")
        self.admin_client = client_for(self.admin)
        self.user_client = client_for(self.alice)

    def test_every_admin_endpoint_rejects_normal_users_and_anonymous(self):
        urls = ["/api/admin/users/", f"/api/admin/users/{self.alice.id}/", "/api/admin/cards/",
                "/api/admin/transactions/", "/api/admin/summary/daily/", "/api/admin/logs/"]
        for url in urls:
            self.assertEqual(self.user_client.get(url).status_code, 403, url)
            self.assertEqual(self.client_class().get(url).status_code, 401, url)

    def test_daily_summary_endpoint(self):
        response = self.admin_client.get("/api/admin/summary/daily/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["success_count"], 1)
        self.assertEqual(Decimal(response.data[0]["success_amount"]), Decimal("20.00"))
        self.assertTrue(AdminLog.objects.filter(action="VIEW_DAILY_SUMMARY").exists())

    def test_daily_summary_validates_dates(self):
        self.assertEqual(self.admin_client.get("/api/admin/summary/daily/?date_from=bad").status_code, 400)
        self.assertEqual(
            self.admin_client.get("/api/admin/summary/daily/?date_from=2030-01-02&date_to=2030-01-01").status_code, 400
        )

    def test_admin_lists_users_cards_transactions_with_masked_data_only(self):
        self.assertEqual(self.admin_client.get("/api/admin/users/").data["count"], 2)
        cards = self.admin_client.get("/api/admin/cards/")
        self.assertEqual(cards.data["count"], 1)
        self.assertEqual(cards.data["results"][0]["masked_number"], "**** **** **** 4242")
        txns = self.admin_client.get("/api/admin/transactions/?status=SUCCESS")
        self.assertEqual(txns.data["results"][0]["user"], "alice")

    def test_admin_can_deactivate_user_and_it_is_logged(self):
        response = self.admin_client.patch(f"/api/admin/users/{self.alice.id}/", {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_active)
        self.assertTrue(AdminLog.objects.filter(action="USER_DEACTIVATED", target_id=str(self.alice.id)).exists())

    def test_admin_cannot_deactivate_self_or_escalate(self):
        self.assertEqual(
            self.admin_client.patch(f"/api/admin/users/{self.admin.id}/", {"is_active": False}, format="json").status_code, 400
        )
        self.admin_client.patch(f"/api/admin/users/{self.alice.id}/", {"is_staff": True, "is_superuser": True}, format="json")
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_staff)

    def test_logs_endpoint(self):
        self.admin_client.get("/api/admin/summary/daily/")
        response = self.admin_client.get("/api/admin/logs/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["admin"], "boss")


class DjangoAdminSiteTests(TestCase):
    def setUp(self):
        self.admin = create_admin()
        self.alice = create_user("alice")
        self.card = create_card(self.alice)
        self.txn = create_transaction(self.alice, self.card, "42.00", "SUCCESS")
        self.client.force_login(self.admin)

    def test_pages_render(self):
        for url in ("/admin/", "/admin/accounts/user/", "/admin/cards/card/", "/admin/transactions/transaction/",
                    "/admin/adminpanel/adminlog/", "/admin/transactions/transaction/daily-summary/",
                    f"/admin/accounts/user/{self.alice.id}/change/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_daily_summary_page_shows_numbers(self):
        response = self.client.get("/admin/transactions/transaction/daily-summary/")
        self.assertContains(response, "42.00")
        self.assertContains(response, "Daily Payment Summary")

    def test_daily_summary_page_ignores_bad_dates(self):
        self.assertEqual(self.client.get("/admin/transactions/transaction/daily-summary/?date_from=zzz").status_code, 200)

    def test_cards_and_transactions_are_read_only(self):
        self.assertEqual(self.client.get("/admin/cards/card/add/").status_code, 403)
        self.assertEqual(self.client.get("/admin/transactions/transaction/add/").status_code, 403)
        self.assertEqual(self.client.post(f"/admin/cards/card/{self.card.id}/delete/").status_code, 403)

    def test_export_action_returns_csv_and_logs(self):
        response = self.client.post(
            "/admin/transactions/transaction/",
            {"action": "export_selected_csv", "_selected_action": [self.txn.id]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(self.txn.reference, response.content.decode())
        self.assertTrue(AdminLog.objects.filter(action="EXPORT_CSV").exists())

    def test_creating_and_editing_users_is_logged(self):
        self.client.post("/admin/accounts/user/add/", {
            "username": "carol", "email": "carol@example.com",
            "password1": "Sup3r#Secret-99", "password2": "Sup3r#Secret-99",
        })
        carol = User.objects.get(username="carol")
        self.assertTrue(AdminLog.objects.filter(action="USER_CREATED", target_id=str(carol.id)).exists())

    def test_non_staff_cannot_open_admin(self):
        self.client.logout()
        self.client.force_login(self.alice)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)  # redirected to login

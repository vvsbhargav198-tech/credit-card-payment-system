from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from testing_utils import PASSWORD, client_for, create_user

REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/token/refresh/"
LOGOUT = "/api/auth/logout/"
ME = "/api/auth/me/"


def payload(**overrides):
    data = {
        "username": "newuser", "email": "New@Example.com", "password": PASSWORD,
        "password_confirm": PASSWORD, "first_name": "New", "last_name": "User",
    }
    data.update(overrides)
    return data


class RegistrationTests(APITestCase):
    def test_register_success_and_response_hides_password(self):
        response = self.client.post(REGISTER, payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "new@example.com")  
        self.assertNotIn("password", response.data)
        self.assertNotIn("password_confirm", response.data)

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"])
    def test_password_is_stored_encrypted_with_pbkdf2(self):
        self.client.post(REGISTER, payload(), format="json")
        user = User.objects.get(username="newuser")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(user.check_password(PASSWORD))

    def test_duplicate_username_rejected(self):
        create_user("newuser")
        response = self.client.post(REGISTER, payload(email="other@example.com"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_duplicate_email_rejected_case_insensitively(self):
        create_user("someone", email="new@example.com")
        response = self.client.post(REGISTER, payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_password_mismatch_rejected(self):
        response = self.client.post(REGISTER, payload(password_confirm="Different#12345"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirm", response.data)

    def test_weak_passwords_rejected(self):
        for weak in ("12345678", "password", "short1"):
            response = self.client.post(REGISTER, payload(password=weak, password_confirm=weak), format="json")
            self.assertEqual(response.status_code, 400, weak)
            self.assertIn("password", response.data)

    def test_invalid_email_and_missing_fields_rejected(self):
        self.assertEqual(self.client.post(REGISTER, payload(email="not-an-email"), format="json").status_code, 400)
        self.assertEqual(self.client.post(REGISTER, {}, format="json").status_code, 400)

    def test_cannot_self_assign_staff_privileges(self):
        self.client.post(REGISTER, payload(is_staff=True, is_superuser=True), format="json")
        user = User.objects.get(username="newuser")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = create_user("alice")

    def test_login_returns_jwt_pair(self):
        response = self.client.post(LOGIN, {"username": "alice", "password": PASSWORD}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_wrong_password_rejected(self):
        response = self.client.post(LOGIN, {"username": "alice", "password": "nope"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(LOGIN, {"username": "alice", "password": PASSWORD}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_sql_injection_attempt_in_login_is_just_a_failed_login(self):
        response = self.client.post(LOGIN, {"username": "alice' OR '1'='1", "password": "x' OR '1'='1"}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(User.objects.count(), 1)


class ProtectedRouteTests(APITestCase):
    def test_me_requires_token(self):
        self.assertEqual(self.client.get(ME).status_code, 401)

    def test_me_rejects_garbage_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not.a.token")
        self.assertEqual(self.client.get(ME).status_code, 401)

    def test_me_rejects_refresh_token_used_as_access(self):
        user = create_user("alice")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user)}")
        self.assertEqual(self.client.get(ME).status_code, 401)

    def test_me_with_valid_token(self):
        user = create_user("alice")
        response = client_for(user).get(ME)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "alice")
        self.assertNotIn("password", response.data)


class LogoutTests(APITestCase):
    def setUp(self):
        self.user = create_user("alice")
        login = self.client.post(LOGIN, {"username": "alice", "password": PASSWORD}, format="json")
        self.access, self.refresh = login.data["access"], login.data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_logout_blacklists_refresh_token(self):
        response = self.client.post(LOGOUT, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, 200)
        # the refresh token can no longer be used to obtain new access tokens
        again = self.client.post(REFRESH, {"refresh": self.refresh}, format="json")
        self.assertEqual(again.status_code, 401)

    def test_logout_twice_fails(self):
        self.client.post(LOGOUT, {"refresh": self.refresh}, format="json")
        self.assertEqual(self.client.post(LOGOUT, {"refresh": self.refresh}, format="json").status_code, 400)

    def test_logout_with_invalid_token(self):
        self.assertEqual(self.client.post(LOGOUT, {"refresh": "garbage"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(LOGOUT, {}, format="json").status_code, 400)

    def test_logout_requires_authentication(self):
        self.client.credentials()
        self.assertEqual(self.client.post(LOGOUT, {"refresh": self.refresh}, format="json").status_code, 401)

    def test_cannot_logout_someone_elses_token(self):
        other = create_user("mallory")
        response = self.client.post(LOGOUT, {"refresh": str(RefreshToken.for_user(other))}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_refresh_rotates_token(self):
        response = self.client.post(REFRESH, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertNotEqual(response.data.get("refresh"), self.refresh)
        self.assertEqual(self.client.post(REFRESH, {"refresh": self.refresh}, format="json").status_code, 401)

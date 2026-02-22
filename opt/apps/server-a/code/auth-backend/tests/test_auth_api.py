from __future__ import annotations

import json
import os
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.test.utils import override_settings
from mongoengine import connect, disconnect
import mongomock

from auth_service import services
from auth_service.constants import LEVEL_ADMIN, LEVEL_CASHIER, LEVEL_MOD, STATUS_BANNED
from auth_service.models import GroupPermission, PasswordResetToken, User, UserGroup, UserSocialLink
from auth_service.social_links import upsert_social_user

BASE_PATH = settings.BASE_PATH or ""


class MongoTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            disconnect(alias="default")
        except Exception:
            pass
        connect("test_auth", alias="default", mongo_client_class=mongomock.MongoClient)

    def setUp(self):
        super().setUp()
        for model in [UserSocialLink, PasswordResetToken, GroupPermission, UserGroup, User]:
            model.drop_collection()
        call_command("seed_defaults")

    def post_json(self, path: str, data: dict[str, object]):
        return self.client.post(f"{BASE_PATH}{path}", data=json.dumps(data), content_type="application/json")

    def get_json(self, path: str):
        return self.client.get(f"{BASE_PATH}{path}")

    def create_user(self, **kwargs) -> User:
        defaults = {
            "email": kwargs.get("email", f"{kwargs.get('full_name', 'user')}@example.com"),
            "phone": None,
            "full_name": kwargs.get("full_name", "Test User"),
            "password": kwargs.get("password", "secret123"),
            "level": kwargs.get("level", LEVEL_CASHIER),
            "status": kwargs.get("status", "Active"),
            "groups": kwargs.get("groups", []),
            "extra_perms": kwargs.get("extra_perms", []),
        }
        return services.create_user(**defaults)

    def login(self, identifier: str, password: str) -> None:
        response = self.post_json("/v1/auth/login", {"identifier": identifier, "password": password})
        self.assertEqual(response.status_code, 200)
        token_cookie = response.cookies.get(settings.COOKIE_NAME)
        self.assertIsNotNone(token_cookie)
        self.client.cookies[settings.COOKIE_NAME] = token_cookie.value


class AuthCookieTests(MongoTestCase):
    def test_login_sets_cookie_contract(self):
        user = self.create_user(email="user1@example.com", password="pass12345")
        response = self.post_json("/v1/auth/login", {"identifier": user.email, "password": "pass12345"})
        self.assertEqual(response.status_code, 200)
        cookie = response.cookies[settings.COOKIE_NAME]
        self.assertFalse(cookie["httponly"])
        self.assertEqual(cookie["domain"], settings.COOKIE_DOMAIN)
        self.assertEqual(cookie["samesite"], settings.COOKIE_SAMESITE)
        self.assertEqual(cookie["path"], "/")

    def test_logout_clears_cookie(self):
        user = self.create_user(email="user2@example.com", password="pass12345")
        self.login(user.email, "pass12345")
        response = self.post_json("/v1/auth/logout", {})
        cookie = response.cookies[settings.COOKIE_NAME]
        self.assertEqual(cookie["max-age"], 0)

    def test_protected_requires_token(self):
        response = self.get_json("/v1/users/me")
        self.assertEqual(response.status_code, 403)


class RBACTests(MongoTestCase):
    def test_user_list_requires_level_and_perm(self):
        mod = self.create_user(
            email="mod@example.com",
            password="Password1!",
            level=LEVEL_MOD,
            groups=["MOD"],
        )
        self.login(mod.email, "Password1!")
        ok_response = self.get_json("/v1/users")
        self.assertEqual(ok_response.status_code, 200)

        cashier = self.create_user(
            email="cashier@example.com",
            password="Password1!",
            level=LEVEL_CASHIER,
            groups=["CASHIER"],
        )
        self.login(cashier.email, "Password1!")
        fail_response = self.get_json("/v1/users")
        self.assertEqual(fail_response.status_code, 403)

    def test_group_endpoints_enforce_permissions(self):
        cashier = self.create_user(email="nope@example.com", password="Password1!", level=LEVEL_CASHIER, groups=["CASHIER"])
        self.login(cashier.email, "Password1!")
        response = self.post_json("/v1/groups", {"code": "QA", "name": "QA"})
        self.assertEqual(response.status_code, 403)

        admin = self.create_user(
            email="admin@example.com",
            password="Password1!",
            level=LEVEL_ADMIN,
            groups=["ADMIN"],
        )
        self.login(admin.email, "Password1!")
        ok_response = self.post_json("/v1/groups", {"code": "QA", "name": "QA"})
        self.assertEqual(ok_response.status_code, 200)


class IntrospectTests(MongoTestCase):
    def test_introspect_reports_active_status(self):
        user = self.create_user(email="active@example.com", password="Password1!", groups=["CUSTOMER"], level="Customer")
        response = self.post_json("/v1/auth/login", {"identifier": user.email, "password": "Password1!"})
        token = response.json()["token"]

        inspector = self.create_user(
            email="inspector@example.com",
            password="Password1!",
            groups=[],
            level=LEVEL_ADMIN,
            extra_perms=["auth.introspect"],
        )
        self.login(inspector.email, "Password1!")
        introspect_response = self.post_json("/v1/auth/introspect", {"token": token})
        self.assertEqual(introspect_response.json()["active"], True)

        services.update_user(user, status=STATUS_BANNED)
        introspect_response = self.post_json("/v1/auth/introspect", {"token": token})
        self.assertEqual(introspect_response.json()["active"], False)


class SocialLinkTests(MongoTestCase):
    def test_upsert_social_user_links_existing_accounts(self):
        user = upsert_social_user(
            provider="google",
            provider_user_id="sub-1",
            email="social@example.com",
            name="Social User",
            email_verified=True,
        )
        same = upsert_social_user(
            provider="google",
            provider_user_id="sub-1",
            email="social@example.com",
            name="Different",
            email_verified=True,
        )
        self.assertEqual(user.id, same.id)

        linked = upsert_social_user(
            provider="microsoft",
            provider_user_id="oid-2",
            email="social@example.com",
            name="Social User",
            email_verified=True,
        )
        self.assertEqual(user.id, linked.id)


class DefaultAdminCommandTests(MongoTestCase):
    def test_create_default_admin_creates_user(self):
        with patch.dict(
            os.environ,
            {
                "DEFAULT_ADMIN_ENABLED": "1",
                "DEFAULT_ADMIN_EMAIL": "admin.seed@example.com",
                "DEFAULT_ADMIN_PASSWORD": "Password1!",
                "DEFAULT_ADMIN_FULL_NAME": "Seed Admin",
                "DEFAULT_ADMIN_GROUPS": "ADMIN",
            },
            clear=False,
        ):
            call_command("create_default_admin")
        user = User.objects(email="admin.seed@example.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.level, LEVEL_ADMIN)
        self.assertEqual(user.groups, ["ADMIN"])

    def test_create_default_admin_requires_password(self):
        with patch.dict(
            os.environ,
            {
                "DEFAULT_ADMIN_ENABLED": "1",
                "DEFAULT_ADMIN_EMAIL": "admin.seed@example.com",
                "DEFAULT_ADMIN_PASSWORD": "",
            },
            clear=False,
        ):
            with self.assertRaises(CommandError):
                call_command("create_default_admin")

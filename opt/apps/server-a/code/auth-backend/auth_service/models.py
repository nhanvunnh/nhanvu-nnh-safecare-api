from __future__ import annotations

from datetime import timedelta

from mongoengine import (  # type: ignore[import]
    BooleanField,
    DateTimeField,
    Document,
    ListField,
    ReferenceField,
    StringField,
    ValidationError,
)

from auth_service import utils
from auth_service.constants import LEVELS, LEVEL_CUSTOMER, STATUSES, STATUS_ACTIVE


class User(Document):
    email = StringField(required=False, unique=True, sparse=True)
    phone = StringField(required=False, unique=True, sparse=True)
    fullName = StringField(required=True)
    passwordHash = StringField(required=True)
    level = StringField(required=True, choices=LEVELS, default=LEVEL_CUSTOMER)
    status = StringField(required=True, choices=STATUSES, default=STATUS_ACTIVE)
    verifiedEmail = BooleanField(default=False)
    verifiedPhone = BooleanField(default=False)
    groups = ListField(StringField(), default=list)
    extraPerms = ListField(StringField(), default=list)
    createdAt = DateTimeField(default=utils.utcnow)
    updatedAt = DateTimeField(default=utils.utcnow)
    lastLoginAt = DateTimeField(required=False)

    meta = {
        "collection": "users",
        "indexes": [
            {"fields": ["email"], "unique": True, "sparse": True},
            {"fields": ["phone"], "unique": True, "sparse": True},
            {"fields": ["level"]},
            {"fields": ["status"]},
        ],
    }

    def clean(self) -> None:
        super().clean()
        if not (self.email or self.phone):
            raise ValidationError("Either email or phone must be set.")
        self.email = utils.normalize_email(self.email)
        self.phone = utils.normalize_phone(self.phone)
        if not (self.email or self.phone):
            raise ValidationError("Email/phone normalization resulted in empty values.")
        if self.groups:
            self.groups = [code.strip().upper() for code in self.groups if code]
        if self.extraPerms:
            self.extraPerms = [perm.strip() for perm in self.extraPerms if perm]

    def save(self, *args, **kwargs):
        self.updatedAt = utils.utcnow()
        return super().save(*args, **kwargs)


class UserGroup(Document):
    code = StringField(required=True, unique=True)
    name = StringField(required=True)
    description = StringField()
    status = StringField(choices=["Active", "Inactive"], default="Active")
    createdAt = DateTimeField(default=utils.utcnow)
    updatedAt = DateTimeField(default=utils.utcnow)

    meta = {
        "collection": "groups",
        "indexes": [
            {"fields": ["code"], "unique": True},
            {"fields": ["status"]},
        ],
    }

    def save(self, *args, **kwargs):
        self.updatedAt = utils.utcnow()
        return super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if self.code:
            self.code = self.code.strip().upper()


class GroupPermission(Document):
    groupCode = StringField(required=True)
    perm = StringField(required=True)
    createdAt = DateTimeField(default=utils.utcnow)

    meta = {
        "collection": "group_permissions",
        "indexes": [
            {"fields": ["groupCode", "perm"], "unique": True},
            {"fields": ["groupCode"]},
        ],
    }

    def clean(self) -> None:
        super().clean()
        if self.groupCode:
            self.groupCode = self.groupCode.strip().upper()
        if self.perm:
            self.perm = self.perm.strip()


class UserSocialLink(Document):
    userId = ReferenceField(User, required=True)
    provider = StringField(required=True, choices=["google", "microsoft"])
    providerUserId = StringField(required=True)
    email = StringField(required=False)
    createdAt = DateTimeField(default=utils.utcnow)

    meta = {
        "collection": "user_social_links",
        "indexes": [
            {"fields": ["provider", "providerUserId"], "unique": True},
            {"fields": ["userId"]},
        ],
    }

    def clean(self) -> None:
        super().clean()
        self.email = utils.normalize_email(self.email)


class PasswordResetToken(Document):
    tokenHash = StringField(required=True, unique=True)
    userId = ReferenceField(User, required=True)
    expiresAt = DateTimeField(required=True)
    used = BooleanField(default=False)
    createdAt = DateTimeField(default=utils.utcnow)

    meta = {
        "collection": "password_reset_tokens",
        "indexes": [
            {"fields": ["tokenHash"], "unique": True},
            {"fields": ["expiresAt"], "expireAfterSeconds": 0},
        ],
    }

    @classmethod
    def build(cls, user: User, ttl_minutes: int, plain_token: str) -> "PasswordResetToken":
        expires_at = utils.utcnow() + timedelta(minutes=ttl_minutes)
        return cls(
            tokenHash=utils.hash_token(plain_token),
            userId=user,
            expiresAt=expires_at,
        )

    def mark_used(self) -> None:
        self.used = True
        self.save()


class ApiToken(Document):
    name = StringField(required=True)
    token = StringField(required=True, unique=True)
    scope = StringField(required=True, choices=["read", "write", "admin"], default="read")
    note = StringField(required=False)
    isActive = BooleanField(default=True)
    expiresAt = DateTimeField(required=False)
    lastUsedAt = DateTimeField(required=False)
    createdBy = StringField(required=False)
    createdAt = DateTimeField(default=utils.utcnow)
    updatedAt = DateTimeField(default=utils.utcnow)

    meta = {
        "collection": "api_tokens",
        "indexes": [
            {"fields": ["token"], "unique": True},
            {"fields": ["isActive", "scope"]},
            {"fields": ["expiresAt"]},
            {"fields": ["createdAt"]},
        ],
    }

    def save(self, *args, **kwargs):
        self.updatedAt = utils.utcnow()
        return super().save(*args, **kwargs)

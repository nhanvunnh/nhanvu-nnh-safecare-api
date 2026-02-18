from __future__ import annotations

from typing import Any

from rest_framework import serializers

from auth_service.constants import LEVELS, STATUSES


class RegisterSerializer(serializers.Serializer):
    usernameType = serializers.ChoiceField(choices=["email", "phone"])
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    password = serializers.CharField(min_length=8, max_length=128)
    fullName = serializers.CharField(max_length=255)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        username_type = attrs.get("usernameType")
        if username_type == "email" and not attrs.get("email"):
            raise serializers.ValidationError("Email required")
        if username_type == "phone" and not attrs.get("phone"):
            raise serializers.ValidationError("Phone required")
        return attrs


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    pass


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    resetToken = serializers.CharField()
    newPassword = serializers.CharField(min_length=8, max_length=128)


class ChangePasswordSerializer(serializers.Serializer):
    oldPassword = serializers.CharField()
    newPassword = serializers.CharField(min_length=8, max_length=128)


class UserMeUpdateSerializer(serializers.Serializer):
    fullName = serializers.CharField(required=False, max_length=255)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs:
            raise serializers.ValidationError("No changes provided")
        return attrs


class UserAdminCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    password = serializers.CharField(required=True, min_length=8, max_length=128)
    fullName = serializers.CharField(max_length=255)
    level = serializers.ChoiceField(choices=LEVELS, default="Customer")
    status = serializers.ChoiceField(choices=STATUSES, default="Active")
    groups = serializers.ListField(child=serializers.CharField(), required=False)
    extraPerms = serializers.ListField(child=serializers.CharField(), required=False)


class UserAdminUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    fullName = serializers.CharField(required=False)
    level = serializers.ChoiceField(choices=LEVELS, required=False)
    status = serializers.ChoiceField(choices=STATUSES, required=False)
    groups = serializers.ListField(child=serializers.CharField(), required=False)
    extraPerms = serializers.ListField(child=serializers.CharField(), required=False)


class GroupSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=["Active", "Inactive"], default="Active")


class GroupPermsSerializer(serializers.Serializer):
    permsAdd = serializers.ListField(child=serializers.CharField(), required=False)
    permsRemove = serializers.ListField(child=serializers.CharField(), required=False)


class UserGroupAssignSerializer(serializers.Serializer):
    groups = serializers.ListField(child=serializers.CharField(), required=True)


class IntrospectSerializer(serializers.Serializer):
    token = serializers.CharField()


class OAuthStateSerializer(serializers.Serializer):
    redirect = serializers.URLField(required=False)


def serialize_user(user, perms: set[str] | None = None) -> dict[str, Any]:
    payload = {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "fullName": user.fullName,
        "level": user.level,
        "status": user.status,
        "groups": list(user.groups or []),
        "extraPerms": list(user.extraPerms or []),
        "verifiedEmail": user.verifiedEmail,
        "verifiedPhone": user.verifiedPhone,
        "lastLoginAt": user.lastLoginAt.isoformat() if user.lastLoginAt else None,
        "createdAt": user.createdAt.isoformat() if user.createdAt else None,
        "updatedAt": user.updatedAt.isoformat() if user.updatedAt else None,
    }
    if perms is not None:
        payload["perms"] = sorted(perms)
    return payload

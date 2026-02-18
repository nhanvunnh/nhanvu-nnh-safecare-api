from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_service import services
from auth_service.constants import STATUS_ACTIVE
from auth_service.email_service import send_reset_email
from auth_service.password_reset import ResetTokenError, consume_reset_token, issue_reset_token
from auth_service.passwords import verify_password
from auth_service.permissions import PrincipalRequired, ensure_level, ensure_perm
from auth_service.rate_limit import RateLimitExceeded, build_rule, check_rate_limit
from auth_service.serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    IntrospectSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    serialize_user,
)
from auth_service.token_service import build_principal_with_token, clear_token_cookie, set_token_cookie
from auth_service.utils import normalize_email


def _client_ip(request) -> str:
    return request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown")).split(",")[0].strip()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data.get("email") if data["usernameType"] == "email" else None
        phone = data.get("phone") if data["usernameType"] == "phone" else None
        if email and services.find_user_by_identifier(email):
            return Response({"ok": False, "error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)
        if phone and services.find_user_by_identifier(phone):
            return Response({"ok": False, "error": "Phone already registered"}, status=status.HTTP_400_BAD_REQUEST)
        user = services.create_user(
            email=email,
            phone=phone,
            full_name=data["fullName"],
            password=data["password"],
        )
        token, principal = build_principal_with_token(user)
        response = Response({"ok": True, "user": serialize_user(user), "token": token})
        set_token_cookie(response, token)
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        identifier_key = normalize_email(data["identifier"]) or data["identifier"]
        rate_key = f"{_client_ip(request)}:{identifier_key}"
        try:
            rule = build_rule("login", rate_key, settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60)
            check_rate_limit(rule)
        except RateLimitExceeded:
            return Response({"ok": False, "error": "Too many attempts"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        user = services.find_user_by_identifier(data["identifier"])
        if not user or not verify_password(data["password"], user.passwordHash):
            return Response({"ok": False, "error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        if user.status != STATUS_ACTIVE:
            return Response({"ok": False, "error": "Account disabled"}, status=status.HTTP_403_FORBIDDEN)
        services.record_login(user)
        token, principal = build_principal_with_token(user)
        response = Response({"ok": True, "user": serialize_user(user), "token": token})
        set_token_cookie(response, token)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response({"ok": True})
        clear_token_cookie(response)
        return response


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        rate_key = f"{_client_ip(request)}:{email}"
        try:
            rule = build_rule("forgot", rate_key, settings.RATE_LIMIT_FORGOT_PER_HOUR, 3600)
            check_rate_limit(rule)
        except RateLimitExceeded:
            return Response({"ok": True})
        user = services.find_user_by_identifier(email)
        if user:
            token = issue_reset_token(user)
            send_reset_email(email, token)
        return Response({"ok": True, "message": "If email exists, we sent instructions."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = consume_reset_token(data["resetToken"])
        except ResetTokenError:
            return Response({"ok": False, "error": "Invalid reset token"}, status=status.HTTP_400_BAD_REQUEST)
        services.set_password(user, data["newPassword"])
        token, principal = build_principal_with_token(user)
        response = Response({"ok": True, "token": token, "user": serialize_user(user)})
        set_token_cookie(response, token)
        return response


class ChangePasswordView(APIView):
    permission_classes = [PrincipalRequired]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        principal = request.principal
        user = services.get_user_by_id(principal.user_id)
        if not user or not verify_password(serializer.validated_data["oldPassword"], user.passwordHash):
            return Response({"ok": False, "error": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)
        services.set_password(user, serializer.validated_data["newPassword"])
        return Response({"ok": True})


class IntrospectView(APIView):
    permission_classes = [PrincipalRequired]

    def post(self, request):
        serializer = IntrospectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        principal = request.principal
        ensure_perm(principal, "auth.introspect")
        from common_auth import jwt as jwt_utils

        token = serializer.validated_data["token"]
        try:
            payload = jwt_utils.verify_jwt(
                token,
                secret=settings.JWT_SECRET,
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE,
            )
        except Exception:
            return Response({"active": False})
        user = services.get_user_by_id(payload.get("sub")) if payload.get("sub") else None
        active = bool(user and user.status == "Active")
        return Response(
            {
                "active": active,
                "sub": payload.get("sub"),
                "level": payload.get("level"),
                "status": payload.get("status"),
                "groups": payload.get("groups", []),
                "perms": payload.get("perms", []),
                "exp": payload.get("exp"),
            }
        )

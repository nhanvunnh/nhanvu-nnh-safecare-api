from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse

from common_auth import jwt as jwt_utils

from auth_service.models import User
from auth_service.principals import build_principal
from auth_service.rbac import get_user_permissions


def build_access_token(user: User) -> tuple[str, set[str]]:
    perms = get_user_permissions(user)
    payload = {
        "sub": str(user.id),
        "level": user.level,
        "status": user.status,
        "groups": list(user.groups or []),
        "perms": list(perms),
    }
    token = jwt_utils.encode_jwt(
        payload,
        secret=settings.JWT_SECRET,
        expires_minutes=settings.JWT_ACCESS_MINUTES,
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
    )
    return token, perms


def set_token_cookie(response: HttpResponse, token: str) -> None:
    max_age = settings.JWT_ACCESS_MINUTES * 60
    response.set_cookie(
        settings.COOKIE_NAME,
        token,
        max_age=max_age,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        httponly=False,
        path="/",
    )


def clear_token_cookie(response: HttpResponse) -> None:
    response.delete_cookie(
        settings.COOKIE_NAME,
        domain=settings.COOKIE_DOMAIN or None,
        path="/",
    )


from common_auth.principal import Principal


def build_principal_with_token(user: User) -> tuple[str, Principal]:
    token, perms = build_access_token(user)
    principal = build_principal(user, perms, token)
    return token, principal

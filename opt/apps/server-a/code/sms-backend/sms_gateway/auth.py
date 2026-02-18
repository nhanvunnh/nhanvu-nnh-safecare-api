from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions, permissions

from .mongo import get_collection
from .utils import sha256_hex


@dataclass
class ApiKeyPrincipal:
    _id: str
    client_name: str
    scopes: list[str]
    rate_limit_per_day: int

    @property
    def is_authenticated(self) -> bool:  # pragma: no cover - simple property
        return True

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


@dataclass
class AgentPrincipal:
    agent_id: str
    device_id: str
    rate_limit_per_min: int

    @property
    def is_authenticated(self) -> bool:
        return True


@dataclass
class JWTUser:
    user_id: str
    username: str
    payload: Dict[str, Any]

    @property
    def is_authenticated(self) -> bool:
        return True


class ApiKeyAuthentication(authentication.BaseAuthentication):
    header_name = "X-API-Key"

    def authenticate(self, request) -> Optional[Tuple[ApiKeyPrincipal, Dict[str, Any]]]:
        api_key = request.headers.get(self.header_name)
        if not api_key:
            return None

        key_hash = sha256_hex(api_key)
        doc = get_collection("api_keys").find_one({"key_hash": key_hash})
        if not doc or not doc.get("is_active", True):
            raise exceptions.AuthenticationFailed("Invalid API key")

        principal = ApiKeyPrincipal(
            _id=str(doc.get("_id")),
            client_name=doc.get("client_name", "client"),
            scopes=doc.get("scopes", []),
            rate_limit_per_day=int(doc.get("rate_limit_per_day", settings.APIKEY_RATE_LIMIT_PER_DAY_DEFAULT)),
        )
        return principal, {"type": "api_key", "doc": doc}


class AgentTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request) -> Optional[Tuple[AgentPrincipal, Dict[str, Any]]]:
        auth_header = authentication.get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None
        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        token = parts[1]
        # JWT tokens contain dots; skip so JWT auth can process
        if "." in token:
            return None

        doc = get_collection("agents").find_one({"token_hash": sha256_hex(token), "is_active": True})
        if not doc:
            raise exceptions.AuthenticationFailed("Invalid agent token")

        principal = AgentPrincipal(
            agent_id=str(doc.get("_id")),
            device_id=doc.get("device_id", ""),
            rate_limit_per_min=int(doc.get("rate_limit_per_min", settings.AGENT_RATE_LIMIT_PER_MIN)),
        )
        return principal, {"type": "agent", "doc": doc, "token": token}


class JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request) -> Optional[Tuple[JWTUser, Dict[str, Any]]]:
        auth_header = authentication.get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None
        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        token = parts[1]
        if "." not in token:
            return None

        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed("Token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed("Invalid token") from exc

        user = JWTUser(
            user_id=str(payload.get("sub")),
            username=payload.get("username", "jwt-user"),
            payload=payload,
        )
        return user, payload


class ApiKeyScopePermission(permissions.BasePermission):
    required_scope: Optional[str] = None

    def has_permission(self, request, view) -> bool:  # pragma: no cover - simple guard
        user = request.user
        if isinstance(user, ApiKeyPrincipal):
            if self.required_scope is None:
                return True
            return user.has_scope(self.required_scope)
        return False


class ApiKeySendPermission(ApiKeyScopePermission):
    required_scope = "sms:send"


class ApiKeyReadPermission(ApiKeyScopePermission):
    required_scope = "sms:read"


class JwtOrApiKeyReadPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if isinstance(user, JWTUser):
            return True
        if isinstance(user, ApiKeyPrincipal):
            return user.has_scope("sms:read")
        return False


class AgentOnlyPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return isinstance(request.user, AgentPrincipal)


class JWTOnlyPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return isinstance(request.user, JWTUser)

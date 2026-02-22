from __future__ import annotations

import secrets
from datetime import timedelta

from django.http import Http404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_service.models import ApiToken
from auth_service.permissions import PrincipalRequired, ensure_level
from auth_service.serializers import ApiTokenCreateSerializer, ApiTokenUpdateSerializer, ApiTokenVerifySerializer
from auth_service.utils import utcnow


_SCOPE_RANK = {"read": 1, "write": 2, "admin": 3}


def _scope_ok(scope: str, required_scope: str) -> bool:
    return _SCOPE_RANK.get((scope or "").lower(), 0) >= _SCOPE_RANK.get((required_scope or "").lower(), 0)


def _is_expired(expires_at) -> bool:
    if not expires_at:
        return False
    now = utcnow()
    # MongoEngine datetimes are typically naive UTC. Align tz-awareness before comparison.
    if getattr(expires_at, "tzinfo", None) is None and getattr(now, "tzinfo", None) is not None:
        now = now.replace(tzinfo=None)
    elif getattr(expires_at, "tzinfo", None) is not None and getattr(now, "tzinfo", None) is None:
        expires_at = expires_at.replace(tzinfo=None)
    return expires_at < now


def _serialize_token(doc: ApiToken, include_token: bool = False) -> dict:
    payload = {
        "id": str(doc.id),
        "name": doc.name,
        "scope": doc.scope,
        "note": doc.note or "",
        "isActive": bool(doc.isActive),
        "expiresAt": doc.expiresAt.isoformat() if doc.expiresAt else None,
        "lastUsedAt": doc.lastUsedAt.isoformat() if doc.lastUsedAt else None,
        "createdBy": doc.createdBy or "",
        "createdAt": doc.createdAt.isoformat() if doc.createdAt else None,
        "updatedAt": doc.updatedAt.isoformat() if doc.updatedAt else None,
        "tokenPreview": (doc.token[:8] + "..." + doc.token[-4:]) if doc.token and len(doc.token) > 16 else doc.token,
    }
    if include_token:
        payload["token"] = doc.token
    return payload


def _get_or_404(token_id: str) -> ApiToken:
    token_doc = ApiToken.objects(id=token_id).first()
    if not token_doc:
        raise Http404("Token not found")
    return token_doc


class ApiTokenCollectionView(APIView):
    permission_classes = [PrincipalRequired]

    def get(self, request):
        ensure_level(request.principal, "Admin")
        page = max(int(request.query_params.get("page", 1)), 1)
        page_size = min(max(int(request.query_params.get("pageSize", 20)), 1), 100)
        scope = request.query_params.get("scope")
        is_active = request.query_params.get("isActive")

        queryset = ApiToken.objects
        if scope:
            queryset = queryset.filter(scope=scope)
        if is_active in {"true", "false"}:
            queryset = queryset.filter(isActive=(is_active == "true"))

        total = queryset.count()
        docs = list(queryset.order_by("-createdAt").skip((page - 1) * page_size).limit(page_size))
        return Response(
            {
                "ok": True,
                "data": [_serialize_token(d) for d in docs],
                "page": page,
                "pageSize": page_size,
                "total": total,
            }
        )

    def post(self, request):
        ensure_level(request.principal, "Admin")
        serializer = ApiTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        plain_token = (data.get("token") or "").strip() or secrets.token_urlsafe(32)
        expires_at = None
        if data.get("expiresDays"):
            expires_at = utcnow() + timedelta(days=int(data["expiresDays"]))

        doc = ApiToken(
            name=data["name"].strip(),
            token=plain_token,
            scope=data.get("scope", "read"),
            note=(data.get("note") or "").strip(),
            isActive=True,
            expiresAt=expires_at,
            createdBy=str(getattr(request.principal, "user_id", "") or ""),
        )
        doc.save()

        return Response({"ok": True, "token": _serialize_token(doc, include_token=True)}, status=status.HTTP_201_CREATED)


class ApiTokenDetailView(APIView):
    permission_classes = [PrincipalRequired]

    def get(self, request, token_id: str):
        ensure_level(request.principal, "Admin")
        doc = _get_or_404(token_id)
        return Response({"ok": True, "token": _serialize_token(doc)})

    def patch(self, request, token_id: str):
        ensure_level(request.principal, "Admin")
        serializer = ApiTokenUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        doc = _get_or_404(token_id)
        data = serializer.validated_data

        for field in ["name", "scope", "note", "isActive", "expiresAt"]:
            if field in data:
                setattr(doc, field, data[field])
        doc.save()

        return Response({"ok": True, "token": _serialize_token(doc)})

    def delete(self, request, token_id: str):
        ensure_level(request.principal, "Admin")
        doc = _get_or_404(token_id)
        doc.delete()
        return Response({"ok": True})


class ApiTokenToggleView(APIView):
    permission_classes = [PrincipalRequired]

    def post(self, request, token_id: str):
        ensure_level(request.principal, "Admin")
        doc = _get_or_404(token_id)
        doc.isActive = not bool(doc.isActive)
        doc.save()
        return Response({"ok": True, "token": _serialize_token(doc)})


class ApiTokenVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ApiTokenVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        required_scope = serializer.validated_data.get("requiredScope", "read")

        doc = ApiToken.objects(token=token, isActive=True).first()
        if not doc:
            return Response({"ok": True, "active": False})

        if _is_expired(doc.expiresAt):
            return Response({"ok": True, "active": False})

        if not _scope_ok(doc.scope, required_scope):
            return Response({"ok": True, "active": False})

        doc.lastUsedAt = utcnow()
        doc.save()
        return Response(
            {
                "ok": True,
                "active": True,
                "scope": doc.scope,
                "name": doc.name,
                "expiresAt": doc.expiresAt.isoformat() if doc.expiresAt else None,
            }
        )

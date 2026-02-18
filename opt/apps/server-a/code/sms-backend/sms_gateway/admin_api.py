from typing import Any, Dict, List

from bson import ObjectId
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import JWTOnlyPermission
from .constants import ActorType, AuditAction
from .mongo import get_collection
from .utils import generate_token, now_utc, sha256_hex, write_audit_log


def serialize_api_key(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc.get("_id")),
        "client_name": doc.get("client_name"),
        "scopes": doc.get("scopes", []),
        "rate_limit_per_day": doc.get("rate_limit_per_day"),
        "is_active": doc.get("is_active", True),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
    }


class ApiKeyListCreateView(APIView):
    permission_classes = [JWTOnlyPermission]

    def get(self, request):
        docs = list(get_collection("api_keys").find().sort("created_at"))
        return Response([serialize_api_key(doc) for doc in docs])

    def post(self, request):
        payload = request.data or {}
        client_name = payload.get("client_name")
        scopes: List[str] = payload.get("scopes") or []
        rate_limit = payload.get("rate_limit_per_day") or payload.get("rate_limit")
        if not client_name or not scopes:
            return Response({"detail": "client_name and scopes required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rate_limit_value = int(rate_limit or settings.APIKEY_RATE_LIMIT_PER_DAY_DEFAULT)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid rate_limit_per_day"}, status=status.HTTP_400_BAD_REQUEST)
        if rate_limit_value <= 0:
            rate_limit_value = settings.APIKEY_RATE_LIMIT_PER_DAY_DEFAULT

        plain_key = generate_token(32)
        doc = {
            "client_name": client_name,
            "scopes": scopes,
            "rate_limit_per_day": rate_limit_value,
            "key_hash": sha256_hex(plain_key),
            "is_active": True,
            "created_at": now_utc(),
            "created_by": getattr(request.user, "username", "user"),
        }
        result = get_collection("api_keys").insert_one(doc)
        doc["_id"] = result.inserted_id
        write_audit_log(ActorType.USER, request.user.user_id, AuditAction.CREATE_API_KEY, {"api_key_id": str(result.inserted_id)})
        response = serialize_api_key(doc)
        response["plain_key"] = plain_key
        return Response(response, status=status.HTTP_201_CREATED)


class ApiKeyDisableView(APIView):
    permission_classes = [JWTOnlyPermission]

    def post(self, request, key_id: str):
        doc = get_collection("api_keys").find_one_and_update(
            {"_id": ObjectId(key_id)},
            {"$set": {"is_active": False, "disabled_at": now_utc(), "disabled_by": getattr(request.user, "username", "user")}},
        )
        if not doc:
            return Response({"detail": "API key not found"}, status=status.HTTP_404_NOT_FOUND)
        write_audit_log(ActorType.USER, request.user.user_id, AuditAction.DISABLE_API_KEY, {"api_key_id": key_id})
        return Response({"status": "ok"})

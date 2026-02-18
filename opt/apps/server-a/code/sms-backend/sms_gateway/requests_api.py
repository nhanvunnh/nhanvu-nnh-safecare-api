from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from bson import ObjectId
from bson.errors import InvalidId
from dateutil import parser
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import ApiKeyPrincipal, ApiKeySendPermission, JwtOrApiKeyReadPermission
from .constants import ActorType, AuditAction, MessagePriority, MessageStatus
PRIORITY_VALUES = {p.value for p in MessagePriority}
PRIORITY_ORDER = {
    MessagePriority.HIGH.value: 0,
    MessagePriority.NORMAL.value: 1,
    MessagePriority.LOW.value: 2,
}

from .mongo import get_collection
from .utils import (
    ensure_uuid,
    now_utc,
    normalize_phone,
    render_template,
    vars_hash,
    write_audit_log,
)


def parse_schedule(value: Any) -> datetime | None:
    if not value:
        return None
    dt = parser.isoparse(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def evaluate_rate_limit(api_key_id: str, day_bucket: str) -> int:
    pipeline = [
        {"$match": {"api_key_id": api_key_id, "day_bucket": day_bucket}},
        {"$group": {"_id": None, "total": {"$sum": "$total_accepted"}}},
    ]
    result = list(get_collection("sms_requests").aggregate(pipeline))
    return result[0]["total"] if result else 0


def resolve_priority(value: Any) -> str:
    if not value:
        return MessagePriority.NORMAL.value
    upper = str(value).upper()
    return upper if upper in PRIORITY_VALUES else MessagePriority.NORMAL.value


def serialize_message(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message_id": doc.get("message_id"),
        "request_id": doc.get("request_id"),
        "to": doc.get("to"),
        "status": doc.get("status"),
        "priority": doc.get("priority"),
        "priority_weight": doc.get("priority_weight"),
        "schedule_at": doc.get("schedule_at").isoformat() if doc.get("schedule_at") else None,
        "lease_until": doc.get("lease_until").isoformat() if doc.get("lease_until") else None,
        "agent_id": doc.get("agent_id"),
        "last_error": doc.get("last_error"),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
    }


class SmsRequestCreateView(APIView):
    permission_classes = [ApiKeySendPermission]

    def post(self, request):
        principal = request.user
        payload = request.data or {}
        template_id = payload.get("template_id")
        messages_payload = payload.get("messages") or []
        default_vars = payload.get("variables") or {}
        default_priority = resolve_priority(payload.get("priority"))
        if not template_id or not messages_payload:
            return Response({"detail": "template_id and messages are required"}, status=status.HTTP_400_BAD_REQUEST)
        if len(messages_payload) > settings.MAX_RECIPIENTS_PER_REQUEST:
            return Response({"detail": "Too many recipients"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            template_oid = ObjectId(template_id)
        except InvalidId:
            return Response({"detail": "Invalid template_id"}, status=status.HTTP_400_BAD_REQUEST)

        template = get_collection("templates").find_one({"_id": template_oid})
        if not template or not template.get("approved"):
            return Response({"detail": "Template not approved"}, status=status.HTTP_400_BAD_REQUEST)

        now = now_utc()
        day_bucket = now.strftime("%Y-%m-%d")
        usage_today = evaluate_rate_limit(principal._id, day_bucket)

        prepared_messages: List[Dict[str, Any]] = []
        duplicate_count = 0
        for msg in messages_payload:
            try:
                normalized_to = normalize_phone(msg.get("to", ""))
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            variables = {**default_vars, **(msg.get("variables") or {})}
            try:
                text = render_template(template.get("content", ""), variables)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if len(text) > settings.MAX_TEXT_LENGTH:
                return Response({"detail": "Text exceeds MAX_TEXT_LENGTH"}, status=status.HTTP_400_BAD_REQUEST)

            schedule_at = parse_schedule(msg.get("schedule_at"))
            vars_digest = vars_hash(variables)
            recent_cutoff = now - timedelta(minutes=settings.ANTI_DUP_MINUTES)
            duplicate = get_collection("sms_messages").find_one(
                {
                    "to": normalized_to,
                    "text": text,
                    "created_at": {"$gte": recent_cutoff},
                }
            )
            priority = resolve_priority(msg.get("priority") or default_priority)
            status_value = MessageStatus.CANCELED.value if duplicate else MessageStatus.PENDING.value
            if duplicate:
                duplicate_count += 1

            prepared_messages.append(
                {
                    "message_id": ensure_uuid(),
                    "request_id": None,
                    "api_key_id": principal._id,
                    "client_name": principal.client_name,
                    "template_id": template_id,
                    "to": normalized_to,
                    "text": text,
                    "variables": variables,
                    "vars_hash": vars_digest,
                    "schedule_at": schedule_at,
                    "status": status_value,
                    "priority": priority,
                    "priority_weight": PRIORITY_ORDER.get(priority, 1),
                    "lease_until": None,
                    "agent_id": None,
                    "attempts": 0,
                    "last_error": "DUPLICATE_RECENT" if duplicate else None,
                    "created_at": now,
                    "updated_at": now,
                    "metadata": payload.get("metadata"),
                }
            )

        accepted = len(prepared_messages) - duplicate_count
        if usage_today + accepted > principal.rate_limit_per_day:
            return Response({"detail": "Daily rate limit exceeded"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        request_id = ensure_uuid()
        for doc in prepared_messages:
            doc["request_id"] = request_id

        get_collection("sms_messages").insert_many(prepared_messages)
        status_counts = Counter(doc["status"] for doc in prepared_messages)

        request_doc = {
            "request_id": request_id,
            "api_key_id": principal._id,
            "client_name": principal.client_name,
            "template_id": template_id,
            "total_created": accepted,
            "total_skipped": duplicate_count,
            "total_accepted": accepted,
            "created_at": now,
            "day_bucket": day_bucket,
            "status_counts": dict(status_counts),
            "metadata": payload.get("metadata"),
        }
        get_collection("sms_requests").insert_one(request_doc)
        write_audit_log(
            ActorType.API_KEY,
            principal._id,
            AuditAction.CREATE_SMS_REQUEST,
            {
                "request_id": request_id,
                "total_created": accepted,
                "total_skipped": duplicate_count,
            },
        )

        return Response(
            {
                "request_id": request_id,
                "total_created": accepted,
                "total_skipped": duplicate_count,
            },
            status=status.HTTP_201_CREATED,
        )


class SmsRequestDetailView(APIView):
    permission_classes = [JwtOrApiKeyReadPermission]

    def get(self, request, request_id: str):
        request_doc = get_collection("sms_requests").find_one({"request_id": request_id})
        if not request_doc:
            return Response({"detail": "Request not found"}, status=status.HTTP_404_NOT_FOUND)
        if isinstance(request.user, ApiKeyPrincipal) and request_doc.get("api_key_id") != request.user._id:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        pipeline = [
            {"$match": {"request_id": request_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        counts = {doc["_id"]: doc["count"] for doc in get_collection("sms_messages").aggregate(pipeline)}
        response = {
            "request_id": request_doc.get("request_id"),
            "template_id": request_doc.get("template_id"),
            "total_created": request_doc.get("total_created", 0),
            "total_skipped": request_doc.get("total_skipped", 0),
            "created_at": request_doc.get("created_at").isoformat() if request_doc.get("created_at") else None,
            "status_counts": counts,
        }
        return Response(response)


class SmsMessageListView(APIView):
    permission_classes = [JwtOrApiKeyReadPermission]

    def get(self, request):
        request_id = request.query_params.get("request_id")
        if not request_id:
            return Response({"detail": "request_id required"}, status=status.HTTP_400_BAD_REQUEST)
        status_filter = request.query_params.get("status")
        try:
            limit = min(int(request.query_params.get("limit", 50)), 500)
            skip = int(request.query_params.get("skip", 0))
        except ValueError:
            return Response({"detail": "limit/skip must be integers"}, status=status.HTTP_400_BAD_REQUEST)

        query: Dict[str, Any] = {"request_id": request_id}
        if status_filter:
            query["status"] = status_filter

        if isinstance(request.user, ApiKeyPrincipal):
            query["api_key_id"] = request.user._id

        cursor = (
            get_collection("sms_messages")
            .find(query)
            .skip(skip)
            .limit(limit)
            .sort("created_at")
        )
        messages = [serialize_message(doc) for doc in cursor]
        return Response({"items": messages, "count": len(messages)})
*** End Patch
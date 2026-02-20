from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Set

from bson import ObjectId
from django.conf import settings
from pymongo import ReturnDocument
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import AgentOnlyPermission, AgentTokenAuthentication
from .config_store import get_registration_secret
from .constants import ActorType, AuditAction, MessageStatus
from .mongo import get_collection
from .utils import ensure_uuid, generate_token, now_utc, sha256_hex, write_audit_log

VALID_MESSAGE_STATUSES: Set[str] = {status.value for status in MessageStatus}
STATUS_TRANSITIONS: Dict[str, Set[str]] = {
    MessageStatus.PENDING.value: {MessageStatus.ASSIGNED.value, MessageStatus.SENDING.value, MessageStatus.SENT.value, MessageStatus.FAILED.value},
    MessageStatus.ASSIGNED.value: {MessageStatus.SENDING.value, MessageStatus.SENT.value, MessageStatus.FAILED.value},
    MessageStatus.SENDING.value: {MessageStatus.SENT.value, MessageStatus.FAILED.value},
    MessageStatus.SENT.value: {MessageStatus.DELIVERED.value},
}


def agent_doc(agent_id: str) -> Dict[str, Any]:
    return get_collection("agents").find_one({"_id": ObjectId(agent_id)})


class AgentRegisterView(APIView):
    authentication_classes: List[Any] = []
    permission_classes: List[Any] = []

    def post(self, request):
        payload = request.data or {}
        device_id = payload.get("device_id")
        label = payload.get("label")
        if not device_id:
            return Response({"detail": "device_id required"}, status=status.HTTP_400_BAD_REQUEST)

        auth_backend = AgentTokenAuthentication()
        try:
            auth_result = auth_backend.authenticate(request)
        except Exception:  # pragma: no cover - best effort fallback
            auth_result = None

        principal = auth_result[0] if auth_result else None
        agents = get_collection("agents")
        now = now_utc()
        existing = agents.find_one({"device_id": device_id})

        if principal:
            existing_agent = agent_doc(principal.agent_id)
            update = {
                "label": label or (existing_agent.get("label") if existing_agent else None),
                "capabilities": payload.get("capabilities") or (existing_agent.get("capabilities") if existing_agent else None),
                "last_seen_at": now,
                "updated_at": now,
            }
            agents.update_one({"_id": ObjectId(principal.agent_id)}, {"$set": update})
            return Response({"status": "ok", "agent_id": principal.agent_id})

        registration_secret = get_registration_secret()
        if registration_secret:
            if payload.get("registration_secret") != registration_secret:
                return Response({"detail": "registration_secret invalid"}, status=status.HTTP_403_FORBIDDEN)

        rotate_token = payload.get("rotate_token") not in {False, "0", 0, "false", "False"}
        if existing:
            if rotate_token:
                plain_token = generate_token(24)
                agents.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"token_hash": sha256_hex(plain_token), "updated_at": now}},
                )
                return Response(
                    {"status": "rotated", "agent_id": str(existing["_id"]), "agent_token": plain_token},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"status": "exists", "agent_id": str(existing["_id"])},
                status=status.HTTP_200_OK,
            )

        plain_token = generate_token(24)
        doc = {
            "device_id": device_id,
            "label": label,
            "capabilities": payload.get("capabilities"),
            "rate_limit_per_min": int(payload.get("rate_limit_per_min") or settings.AGENT_RATE_LIMIT_PER_MIN),
            "token_hash": sha256_hex(plain_token),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "last_seen_at": now,
        }
        result = agents.insert_one(doc)
        return Response(
            {"status": "ok", "agent_id": str(result.inserted_id), "agent_token": plain_token},
            status=status.HTTP_201_CREATED,
        )


class AgentHeartbeatView(APIView):
    permission_classes = [AgentOnlyPermission]

    def post(self, request):
        payload = request.data or {}
        now = now_utc()
        update = {
            "last_seen_at": now,
            "status": payload.get("status", "online"),
            "battery_level": payload.get("battery_level"),
            "app_version": payload.get("app_version"),
            "updated_at": now,
        }
        get_collection("agents").update_one({"_id": ObjectId(request.user.agent_id)}, {"$set": update})
        return Response({"status": "ok"})


class AgentJobsNextView(APIView):
    permission_classes = [AgentOnlyPermission]

    def get(self, request):
        limit = min(int(request.query_params.get("limit", 50)), 200)
        now = now_utc()
        lease_seconds = settings.LEASE_SECONDS
        lease_until = now + timedelta(seconds=lease_seconds)
        collection = get_collection("sms_messages")
        current_agent_id = request.user.agent_id
        messages: List[Dict[str, Any]] = []
        for _ in range(limit):
            doc = collection.find_one_and_update(
                {
                    "$or": [
                        {
                            "agent_id": current_agent_id,
                            "status": MessageStatus.PENDING.value,
                            "$or": [
                                {"schedule_at": None},
                                {"schedule_at": {"$exists": False}},
                                {"schedule_at": {"$lte": now}},
                            ],
                        },
                        {
                            "agent_id": current_agent_id,
                            "status": {"$in": [MessageStatus.ASSIGNED.value, MessageStatus.SENDING.value]},
                            "lease_until": {"$lte": now},
                        },
                    ]
                },
                {
                    "$set": {
                        "status": MessageStatus.ASSIGNED.value,
                        "agent_id": current_agent_id,
                        "lease_until": lease_until,
                        "updated_at": now,
                    },
                    "$inc": {"attempts": 1},
                },
                sort=[("priority_weight", 1), ("created_at", 1)],
                return_document=ReturnDocument.AFTER,
            )
            if not doc:
                break
            messages.append(
                {
                    "message_id": doc.get("message_id"),
                    "request_id": doc.get("request_id"),
                    "to": doc.get("to"),
                    "text": doc.get("text"),
                    "priority": doc.get("priority"),
                    "schedule_at": doc.get("schedule_at").isoformat() if doc.get("schedule_at") else None,
                }
            )

        if messages:
            write_audit_log(
                ActorType.AGENT,
                request.user.agent_id,
                AuditAction.AGENT_LEASE_BATCH,
                {"count": len(messages), "agent_id": request.user.agent_id},
            )

        return Response(
            {
                "batch_id": ensure_uuid(),
                "lease_seconds": lease_seconds,
                "rate_limit_per_min": request.user.rate_limit_per_min,
                "messages": messages,
            }
        )


class AgentReportView(APIView):
    permission_classes = [AgentOnlyPermission]

    def post(self, request):
        payload = request.data or {}
        results = payload.get("messages") or []
        if not results:
            return Response({"detail": "messages required"}, status=status.HTTP_400_BAD_REQUEST)
        collection = get_collection("sms_messages")
        now = now_utc()
        updated = 0

        for item in results:
            message_id = item.get("message_id")
            new_status = item.get("status")
            if not message_id or new_status not in VALID_MESSAGE_STATUSES:
                continue
            doc = collection.find_one({"message_id": message_id})
            if not doc or doc.get("agent_id") not in {None, request.user.agent_id}:
                continue
            current_status = doc.get("status")
            if current_status == MessageStatus.DELIVERED.value:
                continue
            if new_status not in STATUS_TRANSITIONS.get(current_status, set()):
                continue

            update: Dict[str, Any] = {
                "status": new_status,
                "updated_at": now,
                "agent_id": request.user.agent_id,
                "last_error": item.get("last_error"),
            }
            if new_status in {MessageStatus.SENT.value, MessageStatus.FAILED.value, MessageStatus.DELIVERED.value}:
                update["lease_until"] = None
            if new_status == MessageStatus.SENT.value:
                update["sent_at"] = now
            if new_status == MessageStatus.DELIVERED.value:
                update["delivered_at"] = now
            collection.update_one({"_id": doc["_id"]}, {"$set": update})
            updated += 1

        write_audit_log(
            ActorType.AGENT,
            request.user.agent_id,
            AuditAction.AGENT_REPORT_RESULTS,
            {"updated": updated, "agent_id": request.user.agent_id},
        )
        return Response({"updated": updated})

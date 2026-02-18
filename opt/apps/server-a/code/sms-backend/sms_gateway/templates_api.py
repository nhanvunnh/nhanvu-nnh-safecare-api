from typing import Any, Dict, List

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import JWTOnlyPermission
from .constants import ActorType, AuditAction
from .mongo import get_collection
from .utils import extract_template_variables, now_utc, write_audit_log


def serialize_template(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc.get("_id")),
        "name": doc.get("name"),
        "content": doc.get("content"),
        "variables": doc.get("variables", []),
        "approved": doc.get("approved", False),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
        "description": doc.get("description"),
    }


class TemplateListCreateView(APIView):
    permission_classes = [JWTOnlyPermission]

    def get(self, request):
        approved = request.query_params.get("approved", "1")
        query: Dict[str, Any] = {}
        if approved in {"0", "1"}:
            query["approved"] = approved == "1"
        templates = list(get_collection("templates").find(query).sort("created_at"))
        return Response([serialize_template(doc) for doc in templates])

    def post(self, request):
        payload = request.data or {}
        name = payload.get("name")
        content = payload.get("content")
        if not name or not content:
            return Response({"detail": "name and content are required"}, status=status.HTTP_400_BAD_REQUEST)

        variables: List[str] = payload.get("variables") or extract_template_variables(content)
        doc = {
            "name": name,
            "content": content,
            "variables": variables,
            "description": payload.get("description"),
            "approved": False,
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "created_by": getattr(request.user, "username", "system"),
        }
        result = get_collection("templates").insert_one(doc)
        doc["_id"] = result.inserted_id
        write_audit_log(ActorType.USER, request.user.user_id, AuditAction.CREATE_TEMPLATE, {"template_id": str(result.inserted_id)})
        return Response(serialize_template(doc), status=status.HTTP_201_CREATED)


class TemplateDetailView(APIView):
    permission_classes = [JWTOnlyPermission]

    def put(self, request, template_id: str):
        payload = request.data or {}
        updates: Dict[str, Any] = {"updated_at": now_utc()}
        if "name" in payload:
            updates["name"] = payload["name"]
        if "content" in payload:
            updates["content"] = payload["content"]
            updates["variables"] = payload.get("variables") or extract_template_variables(payload["content"])
            updates["approved"] = False
        if "description" in payload:
            updates["description"] = payload["description"]

        try:
            template_oid = ObjectId(template_id)
        except InvalidId:
            return Response({"detail": "Invalid template_id"}, status=status.HTTP_400_BAD_REQUEST)

        result = get_collection("templates").find_one_and_update(
            {"_id": template_oid},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            return Response({"detail": "Template not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_template(result))


class TemplateApproveView(APIView):
    permission_classes = [JWTOnlyPermission]

    def post(self, request, template_id: str):
        try:
            template_oid = ObjectId(template_id)
        except InvalidId:
            return Response({"detail": "Invalid template_id"}, status=status.HTTP_400_BAD_REQUEST)

        doc = get_collection("templates").find_one_and_update(
            {"_id": template_oid},
            {"$set": {"approved": True, "approved_at": now_utc(), "approved_by": getattr(request.user, "username", "system")}},
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return Response({"detail": "Template not found"}, status=status.HTTP_404_NOT_FOUND)
        write_audit_log(ActorType.USER, request.user.user_id, AuditAction.APPROVE_TEMPLATE, {"template_id": str(doc["_id"])})
        return Response(serialize_template(doc))

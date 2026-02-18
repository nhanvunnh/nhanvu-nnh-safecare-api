from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from dateutil import parser
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import JWTOnlyPermission
from .mongo import get_collection


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parser.isoparse(value)
    except ValueError as exc:
        raise ValueError("Invalid date format") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class ReportsSummaryView(APIView):
    permission_classes = [JWTOnlyPermission]

    def get(self, request):
        try:
            date_from = parse_date(request.query_params.get("from"))
            date_to = parse_date(request.query_params.get("to"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        template_id = request.query_params.get("template_id")

        match: Dict[str, Any] = {}
        if template_id:
            match["template_id"] = template_id
        if date_from or date_to:
            match["created_at"] = {}
            if date_from:
                match["created_at"]["$gte"] = date_from
            if date_to:
                match["created_at"]["$lte"] = date_to

        pipeline = [
            {"$match": match or {}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at", "timezone": "UTC"}
                    },
                    "total": {"$sum": 1},
                    "sent": {
                        "$sum": {"$cond": [{"$eq": ["$status", "SENT"]}, 1, 0]},
                    },
                    "delivered": {
                        "$sum": {"$cond": [{"$eq": ["$status", "DELIVERED"]}, 1, 0]},
                    },
                    "failed": {
                        "$sum": {"$cond": [{"$eq": ["$status", "FAILED"]}, 1, 0]},
                    },
                }
            },
            {"$sort": {"_id": 1}},
        ]
        cursor = get_collection("sms_messages").aggregate(pipeline)
        data = [
            {
                "date": doc["_id"],
                "total": doc["total"],
                "sent": doc["sent"],
                "delivered": doc["delivered"],
                "failed": doc["failed"],
            }
            for doc in cursor
        ]
        return Response(data)


class ReportsExportView(APIView):
    permission_classes = [JWTOnlyPermission]

    def get(self, request):
        try:
            date_from = parse_date(request.query_params.get("from"))
            date_to = parse_date(request.query_params.get("to"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        match: Dict[str, Any] = {}
        template_id = request.query_params.get("template_id")
        if template_id:
            match["template_id"] = template_id
        if date_from or date_to:
            match["created_at"] = {}
            if date_from:
                match["created_at"]["$gte"] = date_from
            if date_to:
                match["created_at"]["$lte"] = date_to

        def row_generator() -> Iterable[bytes]:
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["message_id", "request_id", "to", "status", "created_at", "updated_at"])
            yield buffer.getvalue().encode("utf-8")
            buffer.seek(0)
            buffer.truncate(0)
            cursor = get_collection("sms_messages").find(match or {}).sort("created_at")
            for doc in cursor:
                writer.writerow(
                    [
                        doc.get("message_id"),
                        doc.get("request_id"),
                        doc.get("to"),
                        doc.get("status"),
                        doc.get("created_at").isoformat() if doc.get("created_at") else None,
                        doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
                    ]
                )
                yield buffer.getvalue().encode("utf-8")
                buffer.seek(0)
                buffer.truncate(0)

        response = StreamingHttpResponse(row_generator(), content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=reports.csv"
        return response

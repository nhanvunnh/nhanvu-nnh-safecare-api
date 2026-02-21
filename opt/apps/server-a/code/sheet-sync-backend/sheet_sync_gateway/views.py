from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from sheet_sync_gateway.auth import require_auth
from sheet_sync_gateway.models import COL_APP_CONFIGS, COL_JOB_LOGS
from sheet_sync_gateway.mongo import get_collection
from sheet_sync_gateway.sync_engine import SyncEngine
from sheet_sync_gateway.utils import fmt_dt, get_param, parse_int


def error_response(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"Error": str(message)}, status=code)


def obj_response(payload):
    return Response(payload, status=status.HTTP_200_OK)


def paginate(items, page, page_size, window=6):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    sliced = items[start:end]

    start_page = max(1, page - window)
    end_page = min(total_pages, page + window)
    page_numbers = list(range(start_page, end_page + 1))
    return sliced, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "show_first": 1 not in page_numbers,
        "show_last": total_pages not in page_numbers,
        "show_left_ellipsis": (1 not in page_numbers) and start_page > 2,
        "show_right_ellipsis": (total_pages not in page_numbers) and end_page < total_pages - 1,
    }


class SyncAppUpsertView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="admin")
            app_code = str(get_param(request, "app_code", "") or "").strip().lower()
            if not app_code:
                return error_response("Missing app_code")

            fields = get_param(request, "fields", [])
            if not isinstance(fields, list) or not fields:
                return error_response("fields must be non-empty list")

            raw_active = get_param(request, "is_active", True)
            if isinstance(raw_active, str):
                is_active = raw_active.strip().lower() in {"1", "true", "yes", "on"}
            else:
                is_active = bool(raw_active)

            payload = {
                "app_code": app_code,
                "name": str(get_param(request, "name", app_code) or app_code),
                "sheet_name": str(get_param(request, "sheet_name", "") or "").strip(),
                "worksheet_name": str(get_param(request, "worksheet_name", "") or "").strip(),
                "target_db": str(get_param(request, "target_db", "") or "").strip(),
                "target_collection": str(get_param(request, "target_collection", "") or "").strip(),
                "key_field": str(get_param(request, "key_field", "") or "").strip(),
                "updated_at_field": str(get_param(request, "updated_at_field", "UPDATED_AT") or "UPDATED_AT").strip(),
                "date_format": str(get_param(request, "date_format", "%d/%m/%Y %H:%M:%S") or "%d/%m/%Y %H:%M:%S").strip(),
                "fields": [str(f).strip() for f in fields if str(f).strip()],
                "is_active": is_active,
            }

            required_keys = ["sheet_name", "worksheet_name", "target_db", "target_collection", "key_field"]
            for key in required_keys:
                if not payload[key]:
                    return error_response(f"Missing {key}")

            get_collection(COL_APP_CONFIGS).update_one({"app_code": app_code}, {"$set": payload}, upsert=True)
            return obj_response({"ok": True, "data": payload})
        except Exception as exc:
            return error_response(exc)


class SyncAppGetView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="read")
            app_code = str(get_param(request, "app_code", "") or "").strip().lower()
            if not app_code:
                return error_response("Missing app_code")
            cfg = get_collection(COL_APP_CONFIGS).find_one({"app_code": app_code}, {"_id": 0})
            if not cfg:
                return error_response("Not found", code=status.HTTP_404_NOT_FOUND)
            return obj_response({"ok": True, "data": cfg})
        except Exception as exc:
            return error_response(exc)


class SyncAppListView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="read")
            docs = list(get_collection(COL_APP_CONFIGS).find({}, {"_id": 0}).sort("app_code", 1))
            return obj_response({"ok": True, "data": docs})
        except Exception as exc:
            return error_response(exc)


class SyncJobRunView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="write")
            app_code = str(get_param(request, "app_code", "") or "").strip().lower()
            if not app_code:
                return error_response("Missing app_code")

            cfg = get_collection(COL_APP_CONFIGS).find_one({"app_code": app_code, "is_active": True}, {"_id": 0})
            if not cfg:
                return error_response("App config not found or inactive", code=status.HTTP_404_NOT_FOUND)

            direction = str(get_param(request, "direction", "manual") or "manual")
            delete_key = str(get_param(request, "delete_key", "") or "").strip()

            result = SyncEngine().run_two_way(cfg, direction=direction, delete_key=delete_key)
            return obj_response(result)
        except Exception as exc:
            try:
                app_code = str(get_param(request, "app_code", "") or "").strip().lower()
                SyncEngine()._log(app_code or "unknown", "manual", "error", str(exc), stats={})
            except Exception:
                pass
            return error_response(exc)


class SyncLogsListView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="read")
            app_code = str(get_param(request, "app_code", "") or "").strip().lower()
            status_filter = str(get_param(request, "status", "") or "").strip().lower()
            page = parse_int(get_param(request, "page", 1), 1)
            page_size = parse_int(get_param(request, "page_size", 50), 50)
            page_size = max(1, min(page_size, 200))

            query = {}
            if app_code:
                query["app_code"] = app_code
            if status_filter:
                query["status"] = status_filter

            rows = list(get_collection(COL_JOB_LOGS).find(query, {"_id": 0}).sort("timeCreate", -1))
            items, meta = paginate(rows, page, page_size)
            data = []
            for row in items:
                data.append(
                    {
                        "timeCreate": fmt_dt(row.get("timeCreate")),
                        "app_code": row.get("app_code") or "",
                        "direction": row.get("direction") or "",
                        "status": row.get("status") or "",
                        "message": row.get("message") or "",
                        "stats": row.get("stats") or {},
                    }
                )

            return obj_response({"ok": True, "data": data, **meta})
        except Exception as exc:
            return error_response(exc)
